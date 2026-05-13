from pydantic import BaseModel, Field
from uuid import UUID
from typing import List, Optional
from app.config import settings

# REQUÊTES (Rust ->Python)

class FeedRequest(BaseModel):
    user_id: UUID
    limit: int = Field(settings.POLL_REQUEST_LIMIT, ge=1, le=50)
    # Liste des IDs que l'utilisateur a déjà vus pour éviter les doublons
    seen_ids: List[UUID] = []

class InteractionEvent(BaseModel):
    user_id: UUID
    poll_id: UUID
    # vote, skip, share, etc.
    action: str
    duration_ms: Optional[int] = 0


# RÉPONSES (Python-> Rust)
class FeedResponse(BaseModel):
    # On renvoie juste une liste d'IDs ordonnés par pertinence
    poll_ids: List[UUID]
    # On peut ajouter le moteur utilisé (pour du A/B testing plus tard)
    version: str = "v1-base-interests"