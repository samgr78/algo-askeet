from fastapi import APIRouter, Depends
from app.schemas.models import FeedRequest, FeedResponse
from app.infrastructure.db import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/feed", response_model=FeedResponse)
async def get_recommendations(
        request: FeedRequest,
        db: AsyncSession = Depends(get_db)
):
    # Pour l'instant, on fait un mock : on renvoie les seen_ids dans l'autre sens
    # Juste pour tester la validation des UUIDs
    print(f"Demande de feed pour l'utilisateur : {request.user_id}")

    return FeedResponse(
        poll_ids=request.seen_ids,
        version="v1-mock"
    )