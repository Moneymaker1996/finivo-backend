from fastapi import APIRouter, Depends
from .nudge_memory_logic import nudge_user, NudgeRequest, get_db

router = APIRouter(prefix="/voice", tags=["Voice"])

@router.post("/nudge/{user_id}")
async def voice_nudge(user_id: int, request: NudgeRequest, db=Depends(get_db)):
    """Handle voice nudge requests."""
    # Pass source='voice' to nudge_user and await the coroutine
    return await nudge_user(user_id, request, db, source="voice")