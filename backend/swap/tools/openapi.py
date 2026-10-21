"""Print the api's OpenAPI document. Needs no database and no running server.

uv run python -m swap.tools.openapi > ../frontend/openapi.json
"""

import json
import sys

from pydantic import SecretStr

from swap.api.app import create_app
from swap.config import Settings


def main() -> None:
    # Placeholders: building the app never connects or calls anything.
    settings = Settings(
        database_url="postgresql+asyncpg://unused@localhost/unused",
        telegram_bot_token=SecretStr("0:unused"),
    )
    schema = create_app(settings).openapi()
    json.dump(schema, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
