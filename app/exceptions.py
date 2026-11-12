"""
TaskFlow API - Custom Exceptions

``DomainException`` is the base class for domain errors that the global handler
in ``app/main.py`` translates into a 400 response with a stable error code.
Routes currently raise ``HTTPException`` directly, so no subclass is defined
until a route actually needs one (T-115 removed the unused hierarchy).
"""


class DomainException(Exception):
    """
    Base exception for all domain-specific errors.

    Provides a consistent error format with:
    - message: Human-readable error message
    - code: Machine-readable error code

    Attributes:
        message (str): Human-readable error description.
        code (str): Error code for programmatic error handling.
    """

    def __init__(self, message: str, code: str = "DOMAIN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)
