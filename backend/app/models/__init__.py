"""SQLAlchemy model package."""

from importlib import import_module
import pkgutil

from app.models.action_item import ActionItem
from app.models.calendar_connection import CalendarConnection, CalendarConnectionStatus, CalendarProviderType
from app.models.calendar_event import CalendarEvent, CalendarEventStatus
from app.models.chapter import Chapter
from app.models.job import Job, JobStatus, JobType
from app.models.meeting import Meeting
from app.models.participant import Participant
from app.models.summary import Summary
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember, WorkspaceRole


def import_models() -> None:
    """Import model modules so SQLAlchemy metadata is populated."""

    for module_info in pkgutil.iter_modules(__path__):
        if module_info.name.startswith("_") or module_info.name == "mixins":
            continue
        import_module(f"{__name__}.{module_info.name}")


from app.models.notification import Notification, NotificationType

__all__ = [
    "ActionItem",
    "CalendarConnection",
    "CalendarConnectionStatus",
    "CalendarEvent",
    "CalendarEventStatus",
    "CalendarProviderType",
    "Chapter",
    "Job",
    "JobStatus",
    "JobType",
    "Meeting",
    "Notification",
    "NotificationType",
    "Participant",
    "Summary",
    "TranscriptSegment",
    "User",
    "Workspace",
    "WorkspaceMember",
    "WorkspaceRole",
    "import_models",
]
