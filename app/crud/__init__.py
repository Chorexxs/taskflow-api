"""CRUD package (split by domain in T-126).

Names stay importable as ``app.crud.<name>``.
"""

from ._common import *  # noqa: F403
from .activity import *  # noqa: F403
from .attachments import *  # noqa: F403
from .comments import *  # noqa: F403
from .notifications import *  # noqa: F403
from .projects import *  # noqa: F403
from .search import *  # noqa: F403
from .tasks import *  # noqa: F403
from .teams import *  # noqa: F403
from .users import *  # noqa: F403
