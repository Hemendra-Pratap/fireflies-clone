from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.action_item import ActionItem
from app.schemas.intelligence import ActionItemRead, ActionItemUpdate

router = APIRouter()


@router.patch(
    "/{action_item_id}",
    response_model=ActionItemRead,
    status_code=status.HTTP_200_OK,
    summary="Update an action item",
)
def update_action_item(
    action_item_id: int,
    action_item_in: ActionItemUpdate,
    db: Session = Depends(get_db),
) -> ActionItemRead:
    """Update action item status (is_completed) and metadata."""
    item = db.query(ActionItem).filter(ActionItem.id == action_item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action item not found",
        )

    update_data = action_item_in.model_dump(exclude_unset=True)

    if "is_completed" in update_data:
        new_completed = update_data["is_completed"]
        if new_completed and not item.is_completed:
            item.completed_at = datetime.now(timezone.utc)
        elif not new_completed and item.is_completed:
            item.completed_at = None
        item.is_completed = new_completed

    if "description" in update_data and update_data["description"] is not None:
        item.description = update_data["description"].strip()

    if "due_at" in update_data:
        item.due_at = update_data["due_at"]

    if "participant_id" in update_data:
        item.participant_id = update_data["participant_id"]

    db.add(item)
    db.commit()
    db.refresh(item)
    return ActionItemRead.model_validate(item)
