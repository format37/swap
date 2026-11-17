"""Payment details are sealed in the app before they reach the database (kickoff, ADR-0043).

AES-256-GCM with a random 96-bit nonce per seal. The associated data names the person the
details belong to, so a ciphertext copied into someone else's row won't open, while their
own order's details may go on to their own leg of a deal as they are. The keys come from
the environment, never from the database, so a stolen dump or backup holds ciphertext
only. A mask is written alongside, so nothing that only names details needs to decrypt.
"""

import base64
import os
import re
from typing import Any, Literal

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import BaseModel, SecretStr

from swap.errors import DomainError

NONCE_BYTES = 12
# Digits, with single spaces or hyphens between groups: «4276 1234 5678 9012», «123-45-67».
_DIGITS = re.compile(r"\d(?:[ -]?\d)*")


class SealError(Exception):
    """Unknown key id, a tampered envelope, or one moved to another row."""


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class Keys:
    """The keys from RECIPIENT_KEYS="k1:<base64url>,k2:…", sealing with RECIPIENT_KEY_ID.

    To rotate: add a key, make it active, and re-seal old rows; old ids still open.
    """

    def __init__(self, spec: SecretStr, active: str) -> None:
        self._keys: dict[str, AESGCM] = {}
        for part in spec.get_secret_value().split(","):
            kid, _, encoded = part.strip().partition(":")
            try:
                key = _unb64(encoded)
            except ValueError:
                key = b""
            if not kid or len(key) != 32:
                raise ValueError(
                    "RECIPIENT_KEYS holds kid:<32 bytes in base64url>, comma-separated"
                )
            self._keys[kid] = AESGCM(key)
        if active not in self._keys:
            raise ValueError(f"RECIPIENT_KEY_ID {active!r} is not among RECIPIENT_KEYS")
        self.active = active

    def __repr__(self) -> str:
        return f"Keys(active={self.active!r}, ids={sorted(self._keys)!r})"

    def seal(self, plaintext: SecretStr, aad: str) -> dict[str, Any]:
        """The JSONB envelope for `plaintext`, bound to the row `aad` names."""
        nonce = os.urandom(NONCE_BYTES)
        text = plaintext.get_secret_value()
        sealed = self._keys[self.active].encrypt(nonce, text.encode(), aad.encode())
        return Envelope(
            kid=self.active, nonce=_b64(nonce), ct=_b64(sealed), mask=mask(text)
        ).model_dump()

    def unseal(self, envelope: dict[str, Any], aad: str) -> SecretStr:
        sealed = Envelope.model_validate(envelope)
        cipher = self._keys.get(sealed.kid)
        if cipher is None:
            raise SealError(f"unknown key id {sealed.kid!r}")
        try:
            text = cipher.decrypt(_unb64(sealed.nonce), _unb64(sealed.ct), aad.encode())
        except InvalidTag as exc:
            raise SealError("the envelope doesn't open here") from exc
        return SecretStr(text.decode())


class Envelope(BaseModel):
    v: Literal[1] = 1
    kid: str
    nonce: str
    ct: str
    # Shown instead of the text to everyone but those Q-B8 allows.
    mask: str


def mask(text: str) -> str:
    """«•••• 5678»: the last four digits of the longest run of digits; «•••» without one.

    Enough for the payee to recognise their card, too little to use it.
    """
    runs = [re.sub(r"\D", "", run) for run in _DIGITS.findall(text)]
    longest = max(runs, key=len, default="")
    return f"•••• {longest[-4:]}" if len(longest) >= 4 else "•••"


def new_key() -> str:
    """A fresh key in RECIPIENT_KEYS's form, for whoever sets up a server."""
    return _b64(AESGCM.generate_key(bit_length=256))


def details_aad(owner_id: object) -> str:
    """Whose details these are: the author of an order, or the payee of a leg."""
    return f"swap/details/{owner_id}/v1"


def seal_details(keys: Keys | None, owner: object, text: str | None) -> dict[str, Any] | None:
    """`owner`'s payment details as stored; None for none. Refused where there is no key."""
    text = (text or "").strip()
    if not text:
        return None
    if keys is None:
        raise DomainError(503, "details.off")
    return keys.seal(SecretStr(text), details_aad(owner))


def open_details(keys: Keys | None, owner: object, sealed: dict[str, Any] | None) -> str | None:
    """The text of `owner`'s details, for those allowed to read them."""
    if sealed is None or keys is None:
        return None
    return keys.unseal(sealed, details_aad(owner)).get_secret_value()
