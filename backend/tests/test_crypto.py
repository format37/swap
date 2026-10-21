"""Sealed payment details (ADR-0004): AES-GCM, bound to their row, keys outside the database."""

import uuid

import pytest
from pydantic import SecretStr

from swap.crypto import Keys, SealError, mask, new_key, payment_method_aad

CARD = SecretStr("Сбербанк, карта 4276 1234 5678 9012, Иванова Н.")


@pytest.fixture
def keys() -> Keys:
    return Keys(SecretStr(f"k1:{new_key()}"), "k1")


def test_a_sealed_text_opens_only_for_its_own_row(keys: Keys) -> None:
    row = uuid.uuid4()
    envelope = keys.seal(CARD, payment_method_aad(row))
    assert (
        keys.unseal(envelope, payment_method_aad(row)).get_secret_value() == CARD.get_secret_value()
    )
    # Copied into another row, it doesn't open.
    with pytest.raises(SealError):
        keys.unseal(envelope, payment_method_aad(uuid.uuid4()))


def test_the_envelope_holds_no_plaintext(keys: Keys) -> None:
    envelope = keys.seal(CARD, payment_method_aad(uuid.uuid4()))
    assert set(envelope) == {"v", "kid", "nonce", "ct", "mask"}
    flat = str(envelope)
    for fragment in ("4276", "1234 5678", "Иванова", "Сбербанк"):
        assert fragment not in flat
    assert envelope["mask"] == "•••• 9012"


def test_every_seal_has_its_own_nonce(keys: Keys) -> None:
    aad = payment_method_aad(uuid.uuid4())
    first, second = keys.seal(CARD, aad), keys.seal(CARD, aad)
    assert first["nonce"] != second["nonce"]
    assert first["ct"] != second["ct"]


def test_a_tampered_envelope_doesnt_open(keys: Keys) -> None:
    aad = payment_method_aad(uuid.uuid4())
    envelope = keys.seal(CARD, aad)
    flipped = envelope["ct"][:-2] + ("A" if envelope["ct"][-2] != "A" else "B") + envelope["ct"][-1]
    with pytest.raises(SealError):
        keys.unseal({**envelope, "ct": flipped}, aad)


def test_an_old_key_still_opens_after_rotation() -> None:
    old = new_key()
    before = Keys(SecretStr(f"k1:{old}"), "k1")
    aad = payment_method_aad(uuid.uuid4())
    envelope = before.seal(CARD, aad)
    after = Keys(SecretStr(f"k1:{old},k2:{new_key()}"), "k2")
    assert after.unseal(envelope, aad).get_secret_value() == CARD.get_secret_value()
    assert after.seal(CARD, aad)["kid"] == "k2"
    with pytest.raises(SealError):
        Keys(SecretStr(f"k2:{new_key()}"), "k2").unseal(envelope, aad)


@pytest.mark.parametrize(
    ("spec", "active"),
    [("k1:short", "k1"), (f"k1:{new_key()}", "k9"), ("", "k1"), (f":{new_key()}", "")],
)
def test_bad_key_settings_fail_loudly(spec: str, active: str) -> None:
    with pytest.raises(ValueError, match="RECIPIENT_KEY"):
        Keys(SecretStr(spec), active)


def test_keys_never_print(keys: Keys) -> None:
    assert "k1" in repr(keys)
    assert new_key()[:8] not in repr(keys)


@pytest.mark.parametrize(
    ("text", "masked"),
    [
        ("4276 1234 5678 9012", "•••• 9012"),
        ("4276123456789012", "•••• 9012"),
        ("+7 999 123-45-67, Нино", "•••• 4567"),
        ("GE29TB0000000000000001", "•••• 0001"),
        ("USDT TRC20: TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t", "•••"),
        ("Наличные у метро Руставели", "•••"),
        ("", "•••"),
    ],
)
def test_the_mask_shows_the_last_four_digits(text: str, masked: str) -> None:
    assert mask(text) == masked
