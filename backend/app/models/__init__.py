"""SQLAlchemy model package."""

from importlib import import_module
import pkgutil

from app.models.action_item import ActionItem
from app.models.chapter import Chapter
from app.models.meeting import Meeting
from app.models.participant import Participant
from app.models.summary import Summary
from app.models.transcript_segment import TranscriptSegment


def import_models() -> None:
    """Import model modules so SQLAlchemy metadata is populated."""

    for module_info in pkgutil.iter_modules(__path__):
        if module_info.name.startswith("_") or module_info.name == "mixins":
            continue
        import_module(f"{__name__}.{module_info.name}")


__all__ = [
    "ActionItem",
    "Chapter",
    "Meeting",
    "Participant",
    "Summary",
    "TranscriptSegment",
    "import_models",
]
