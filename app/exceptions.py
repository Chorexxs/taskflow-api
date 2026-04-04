class DomainException(Exception):
    def __init__(self, message: str, code: str = "DOMAIN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class TeamNotFound(DomainException):
    def __init__(self, team_id_or_slug: str):
        super().__init__(
            message=f"Team not found: {team_id_or_slug}",
            code="TEAM_NOT_FOUND"
        )


class ProjectNotFound(DomainException):
    def __init__(self, project_id_or_slug: str):
        super().__init__(
            message=f"Project not found: {project_id_or_slug}",
            code="PROJECT_NOT_FOUND"
        )


class TaskNotFound(DomainException):
    def __init__(self, task_id_or_title: str):
        super().__init__(
            message=f"Task not found: {task_id_or_title}",
            code="TASK_NOT_FOUND"
        )


class NotAMember(DomainException):
    def __init__(self, user_id: int, team_id: int):
        super().__init__(
            message=f"User {user_id} is not a member of team {team_id}",
            code="NOT_A_MEMBER"
        )


class NotTeamAdmin(DomainException):
    def __init__(self, user_id: int, team_id: int):
        super().__init__(
            message=f"User {user_id} is not an admin of team {team_id}",
            code="NOT_TEAM_ADMIN"
        )


class PermissionDenied(DomainException):
    def __init__(self, action: str):
        super().__init__(
            message=f"Permission denied: {action}",
            code="PERMISSION_DENIED"
        )


class UserNotFound(DomainException):
    def __init__(self, user_id: int):
        super().__init__(
            message=f"User not found: {user_id}",
            code="USER_NOT_FOUND"
        )


class InvalidCredentials(DomainException):
    def __init__(self):
        super().__init__(
            message="Invalid email or password",
            code="INVALID_CREDENTIALS"
        )


class EmailAlreadyRegistered(DomainException):
    def __init__(self, email: str):
        super().__init__(
            message=f"Email already registered: {email}",
            code="EMAIL_ALREADY_REGISTERED"
        )


class InvalidToken(DomainException):
    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message=message, code="INVALID_TOKEN")


class AccountLocked(DomainException):
    def __init__(self):
        super().__init__(
            message="Account temporarily locked due to too many failed login attempts",
            code="ACCOUNT_LOCKED"
        )
