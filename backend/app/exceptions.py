"""Domain exceptions mapped to HTTP responses in app.main."""


class DomainError(Exception):
    """Base class for errors the API turns into a clean JSON response."""

    status_code = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    status_code = 404


class ConflictError(DomainError):
    status_code = 409
