from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

from swap.init_data import validate_init_data
from swap.tools.dev_launch import launch_url
from tests.conftest import TEST_BOT_TOKEN


def test_the_dev_launch_url_passes_the_real_validation() -> None:
    now = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)
    url = launch_url(
        "http://localhost:5180/",
        TEST_BOT_TOKEN,
        user_id=7,
        first_name="Нино",
        username="nino",
        language_code="ka",
        theme="dark",
        now=int(now.timestamp()),
    )
    parts = urlsplit(url)
    assert f"{parts.scheme}://{parts.netloc}{parts.path}" == "http://localhost:5180/"
    params = parse_qs(parts.fragment)
    # What the SDK hands the api: tgWebAppData, decoded once.
    [init_data] = params["tgWebAppData"]
    launch = validate_init_data(init_data, TEST_BOT_TOKEN, max_age=timedelta(hours=1), now=now)
    assert launch.user.id == 7
    assert launch.user.first_name == "Нино"
    assert launch.user.language_code == "ka"
    assert params["tgWebAppPlatform"] == ["tdesktop"]
