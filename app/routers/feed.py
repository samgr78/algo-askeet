from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.db import get_db
from app.schemas.models import FeedRequest, FeedResponse
from app.scoring.engine import get_personalized_feed

router = APIRouter()


@router.post("/feed", response_model=FeedResponse)
async def get_feed(request: FeedRequest, db: AsyncSession = Depends(get_db)):
    try:
        # On appelle le moteur de scoring
        recommendations = await get_personalized_feed(
            db,
            request.user_id,
            request.limit,
            request.seen_ids
        )

        return FeedResponse(
            poll_ids=recommendations,
            version="v1-interest-based"
        )
    except Exception as e:
        # En cas d'erreur, on logue et on renvoie une 500
        print(f"Erreur Algo: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du calcul du feed")