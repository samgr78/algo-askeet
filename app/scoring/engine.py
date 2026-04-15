from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List


async def get_personalized_feed(
        db: AsyncSession,
        user_id: UUID,
        limit: int,
        seen_ids: List[UUID]
) -> List[UUID]:
    # 1. Récupérer les catégories préférées de l'utilisateur
    # On cherche dans la table pivot user_category
    user_interests_query = await db.execute(
        text("SELECT category_id FROM user_category WHERE user_id = :uid"),
        {"uid": user_id.bytes}
    )
    user_categories = [row[0] for row in user_interests_query.fetchall()]

    # 2. Récupérer les sondages candidats
    # On exclut ceux que l'utilisateur a déjà vus
    # On récupère l'ID et la catégorie pour le scoring
    query_str = "SELECT id, category_id FROM surveys"
    if seen_ids:
        query_str += " WHERE id NOT IN :seen"

    surveys_query = await db.execute(
        text(query_str),
        {"seen": [s.bytes for s in seen_ids]} if seen_ids else {}
    )
    all_surveys = surveys_query.fetchall()

    # 3. Calcul du score pour chaque sondage
    scored_surveys = []
    for s_id, s_cat_id in all_surveys:
        score = 0

        # Bonus si le sondage correspond aux goûts de l'user
        if s_cat_id in user_categories:
            score += 100  # Gros bonus pour la pertinence

        # Ici on pourrait ajouter un score de "fraîcheur" ou de "popularité"
        # score += popularité * 0.5

        scored_surveys.append((UUID(bytes=s_id), score))

    # 4. Tri par score décroissant
    scored_surveys.sort(key=lambda x: x[1], reverse=True)

    # 5. Retourne uniquement les IDs ordonnés (tronqués par la limite)
    return [s[0] for s in scored_surveys[:limit]]