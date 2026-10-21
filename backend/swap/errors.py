"""Errors of the rules themselves, raised wherever the rule lives.

The api answers one as an RFC 9457 problem with its status and machine `code`
(swap/api/errors.py), and the UI turns the code into words (ADR-0007, ADR-0009).
"""


class DomainError(Exception):
    """A request the rules don't allow, such as answering someone else's link request."""

    def __init__(self, status: int, code: str, detail: str | None = None) -> None:
        super().__init__(code)
        self.status = status
        self.code = code
        self.detail = detail
