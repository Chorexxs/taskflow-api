"""Team search response."""

from pydantic import BaseModel

from .projects import PaginatedProjectResponse
from .tasks import PaginatedTaskResponse

__all__ = [
    "SearchResult",
]


class SearchResult(BaseModel):
    """Paginated search results for projects and tasks."""

    projects: PaginatedProjectResponse
    tasks: PaginatedTaskResponse
