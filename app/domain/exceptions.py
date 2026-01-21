"""Domain-level exceptions for business logic errors"""

class DomainException(Exception):
    """Base exception for domain errors"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ResourceNotFoundError(DomainException):
    """Raised when a requested resource is not found"""
    def __init__(self, resource: str, identifier: any):
        super().__init__(f"{resource} with id {identifier} not found", 404)


class DuplicateResourceError(DomainException):
    """Raised when attempting to create a duplicate resource"""
    def __init__(self, resource: str, field: str, value: any):
        super().__init__(f"{resource} with {field} '{value}' already exists", 400)


class UnauthorizedError(DomainException):
    """Raised when user is not authorized"""
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, 401)


class ForbiddenError(DomainException):
    """Raised when user lacks permission"""
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, 403)


class ValidationError(DomainException):
    """Raised when business validation fails"""
    def __init__(self, message: str):
        super().__init__(message, 400)


class AccountLockedError(DomainException):
    """Raised when account is locked due to failed login attempts"""
    def __init__(self, minutes_remaining: int):
        super().__init__(
            f"Too many failed login attempts. Account locked. Try again in {minutes_remaining} minute(s).",
            401
        )


class InactiveTenantError(DomainException):
    """Raised when tenant is inactive"""
    def __init__(self):
        super().__init__("Invalid credentials", 401)  # Don't reveal tenant status


class InactiveUserError(DomainException):
    """Raised when user is inactive"""
    def __init__(self):
        super().__init__("Inactive user", 400)
