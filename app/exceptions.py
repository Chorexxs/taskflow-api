"""
TaskFlow API - Custom Exceptions

This module defines custom exception classes used throughout the application.
All exceptions inherit from DomainException which provides a consistent
error response format with error codes and messages.

Exception Hierarchy:
- DomainException (base)
  - TeamNotFound
  - ProjectNotFound
  - TaskNotFound
  - NotAMember
  - NotTeamAdmin
  - PermissionDenied
  - UserNotFound
  - InvalidCredentials
  - EmailAlreadyRegistered
  - InvalidToken
  - AccountLocked

These exceptions are handled in app/main.py by the domain_exception_handler
which returns them as 400 errors with the error code and message.
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


class TeamNotFound(DomainException):
    """
    Exception raised when a team is not found.
    
    Raised when attempting to access a team with an invalid ID or slug.
    """
    def __init__(self, team_id_or_slug: str):
        """
        Initialize TeamNotFound exception.
        
        Args:
            team_id_or_slug (str): The team identifier that was not found.
        """
        super().__init__(
            message=f"Team not found: {team_id_or_slug}",
            code="TEAM_NOT_FOUND"
        )


class ProjectNotFound(DomainException):
    """
    Exception raised when a project is not found.
    
    Raised when attempting to access a project with an invalid ID or name.
    """
    def __init__(self, project_id_or_slug: str):
        """
        Initialize ProjectNotFound exception.
        
        Args:
            project_id_or_slug (str): The project identifier that was not found.
        """
        super().__init__(
            message=f"Project not found: {project_id_or_slug}",
            code="PROJECT_NOT_FOUND"
        )


class TaskNotFound(DomainException):
    """
    Exception raised when a task is not found.
    
    Raised when attempting to access a task with an invalid ID or title.
    """
    def __init__(self, task_id_or_title: str):
        """
        Initialize TaskNotFound exception.
        
        Args:
            task_id_or_title (str): The task identifier that was not found.
        """
        super().__init__(
            message=f"Task not found: {task_id_or_title}",
            code="TASK_NOT_FOUND"
        )


class NotAMember(DomainException):
    """
    Exception raised when a user is not a member of a team.
    
    Raised when accessing team resources without membership.
    """
    def __init__(self, user_id: int, team_id: int):
        """
        Initialize NotAMember exception.
        
        Args:
            user_id (int): ID of the user who is not a member.
            team_id (int): ID of the team.
        """
        super().__init__(
            message=f"User {user_id} is not a member of team {team_id}",
            code="NOT_A_MEMBER"
        )


class NotTeamAdmin(DomainException):
    """
    Exception raised when a user is not an admin of a team.
    
    Raised when attempting admin-only operations without admin privileges.
    """
    def __init__(self, user_id: int, team_id: int):
        """
        Initialize NotTeamAdmin exception.
        
        Args:
            user_id (int): ID of the user who is not an admin.
            team_id (int): ID of the team.
        """
        super().__init__(
            message=f"User {user_id} is not an admin of team {team_id}",
            code="NOT_TEAM_ADMIN"
        )


class PermissionDenied(DomainException):
    """
    Exception raised when a user lacks permission for an action.
    
    Raised for general permission issues not covered by other exceptions.
    """
    def __init__(self, action: str):
        """
        Initialize PermissionDenied exception.
        
        Args:
            action (str): Description of the action that was denied.
        """
        super().__init__(
            message=f"Permission denied: {action}",
            code="PERMISSION_DENIED"
        )


class UserNotFound(DomainException):
    """
    Exception raised when a user is not found.
    
    Raised when attempting to access a user with an invalid ID.
    """
    def __init__(self, user_id: int):
        """
        Initialize UserNotFound exception.
        
        Args:
            user_id (int): ID of the user that was not found.
        """
        super().__init__(
            message=f"User not found: {user_id}",
            code="USER_NOT_FOUND"
        )


class InvalidCredentials(DomainException):
    """
    Exception raised when login credentials are invalid.
    
    Raised during authentication when email or password is incorrect.
    """
    def __init__(self):
        """
        Initialize InvalidCredentials exception.
        """
        super().__init__(
            message="Invalid email or password",
            code="INVALID_CREDENTIALS"
        )


class EmailAlreadyRegistered(DomainException):
    """
    Exception raised when registering with an existing email.
    
    Raised during user registration when the email is already in use.
    """
    def __init__(self, email: str):
        """
        Initialize EmailAlreadyRegistered exception.
        
        Args:
            email (str): The email that is already registered.
        """
        super().__init__(
            message=f"Email already registered: {email}",
            code="EMAIL_ALREADY_REGISTERED"
        )


class InvalidToken(DomainException):
    """
    Exception raised when a token is invalid or expired.
    
    Raised during token validation when the token is malformed,
    expired, or has been revoked.
    """
    def __init__(self, message: str = "Invalid or expired token"):
        """
        Initialize InvalidToken exception.
        
        Args:
            message (str): Specific error message. Defaults to generic message.
        """
        super().__init__(message=message, code="INVALID_TOKEN")


class AccountLocked(DomainException):
    """
    Exception raised when an account is locked due to security reasons.
    
    Raised when a user has exceeded the maximum number of failed
    login attempts and their account is temporarily locked.
    """
    def __init__(self):
        """
        Initialize AccountLocked exception.
        """
        super().__init__(
            message="Account temporarily locked due to too many failed login attempts",
            code="ACCOUNT_LOCKED"
        )
