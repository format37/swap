"""Print a fresh key for sealing payment details (ADR-0004), as RECIPIENT_KEYS wants it.

    uv run python -m swap.tools.new_key          → k1:<base64url>
    uv run python -m swap.tools.new_key --id k2  → k2:<base64url>, for a rotation

It goes into the server's .env only. Keep a copy off the server: without it, the saved
payment details can't be read back.
"""

import argparse

from swap.crypto import new_key


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--id", default="k1", help="the key's id")
    print(f"{parser.parse_args().id}:{new_key()}")


if __name__ == "__main__":
    main()
