"""Print a launch URL for testing the Mini App in a desktop browser (ADR-0011).

    TELEGRAM_BOT_TOKEN=… uv run python -m swap.tools.dev_launch --lang ka

The URL carries launch parameters in its hash, the way Telegram passes them, with
initData signed by TELEGRAM_BOT_TOKEN, so the api validates it like any real launch.
Nothing on the server is bypassed. It expires with INIT_DATA_MAX_AGE_S (an hour by
default), and it signs in whoever it names, so keep it to yourself.
"""

import argparse
import base64
import json
import os
import secrets
import time
from urllib.parse import quote, urlencode

from swap.init_data import sign

# Telegram's own default palettes, close enough to see the app as it will look.
THEMES = {
    "light": {
        "bg_color": "#ffffff",
        "text_color": "#000000",
        "hint_color": "#707579",
        "link_color": "#3390ec",
        "button_color": "#3390ec",
        "button_text_color": "#ffffff",
        "secondary_bg_color": "#f4f4f5",
        "section_bg_color": "#ffffff",
        "section_separator_color": "#e7e7e7",
        "section_header_text_color": "#707579",
        "subtitle_text_color": "#707579",
        "accent_text_color": "#3390ec",
        "destructive_text_color": "#e53935",
        "header_bg_color": "#ffffff",
        "bottom_bar_bg_color": "#ffffff",
    },
    "dark": {
        "bg_color": "#212121",
        "text_color": "#ffffff",
        "hint_color": "#aaaaaa",
        "link_color": "#8774e1",
        "button_color": "#8774e1",
        "button_text_color": "#ffffff",
        "secondary_bg_color": "#181818",
        "section_bg_color": "#212121",
        "section_separator_color": "#303030",
        "section_header_text_color": "#aaaaaa",
        "subtitle_text_color": "#aaaaaa",
        "accent_text_color": "#8774e1",
        "destructive_text_color": "#e53935",
        "header_bg_color": "#212121",
        "bottom_bar_bg_color": "#212121",
    },
}


def launch_url(
    base: str,
    bot_token: str,
    *,
    user_id: int,
    first_name: str,
    username: str | None,
    language_code: str,
    theme: str,
    photo_url: str | None = None,
    now: int | None = None,
) -> str:
    user: dict[str, object] = {
        "id": user_id,
        "first_name": first_name,
        "username": username,
        "language_code": language_code,
        "allows_write_to_pm": True,
    }
    if photo_url:
        user["photo_url"] = photo_url
    fields = {
        "query_id": "AAHdevlaunch",
        "user": json.dumps(user, ensure_ascii=False, separators=(",", ":")),
        "auth_date": str(now if now is not None else int(time.time())),
        # Telegram has sent an Ed25519 `signature` since Bot API 8.0, and the SDK refuses
        # launch parameters without one. Nothing of ours checks it as Ed25519; like
        # every other field it is covered by the HMAC.
        "signature": base64.urlsafe_b64encode(secrets.token_bytes(64)).decode().rstrip("="),
    }
    init_data = urlencode({**fields, "hash": sign(fields, bot_token)}, quote_via=quote)
    params = {
        "tgWebAppData": init_data,
        "tgWebAppVersion": "9.0",
        "tgWebAppPlatform": "tdesktop",
        "tgWebAppThemeParams": json.dumps(THEMES[theme], separators=(",", ":")),
    }
    return f"{base.rstrip('/')}/#{urlencode(params, quote_via=quote)}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="http://localhost:5180", help="the app's origin")
    parser.add_argument("--user-id", type=int, default=1001)
    parser.add_argument("--name", default="Alex")
    parser.add_argument("--username", default="dev_alex")
    parser.add_argument("--lang", default="ru", help="Telegram's language_code")
    parser.add_argument("--theme", choices=sorted(THEMES), default="light")
    # A public userpic serves well: https://t.me/i/userpic/320/<username>.jpg (ADR-0027).
    parser.add_argument("--photo", help="a photo_url, as Telegram would send it")
    args = parser.parse_args()
    print(
        launch_url(
            args.base,
            os.environ["TELEGRAM_BOT_TOKEN"],
            user_id=args.user_id,
            first_name=args.name,
            username=args.username,
            language_code=args.lang,
            theme=args.theme,
            photo_url=args.photo,
        )
    )


if __name__ == "__main__":
    main()
