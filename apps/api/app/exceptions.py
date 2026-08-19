class DomainError(Exception):
    status_code = 400


class ValidationError(DomainError):
    status_code = 422


class AuthorizationError(DomainError):
    status_code = 403


class NotFoundError(DomainError):
    status_code = 404


class ConflictError(DomainError):
    status_code = 409
