from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Set
from datetime import datetime, timezone


# --- FONCTION DE RÉCUPÉRATION DES PREFERENCE AVEC LES TAGS LIKE RECEMENT ---

async def get_user_favorite_tags(db: AsyncSession, user_id: UUID) -> Set[bytes]:
    """
    Analyse l'historique de l'utilisateur pour trouver les tags qu'il aime.
    """
    query = text("""
                 SELECT st.tag_id, COUNT(*) as frequency
                 FROM survey_tags st
                     JOIN votes v ON st.survey_id = v.poll_id
                 WHERE v.user_id = :uid
                   AND v.type = 'up'
                 GROUP BY st.tag_id
                 ORDER BY frequency DESC LIMIT 20
                 """)

    result = await db.execute(query, {"uid": user_id.bytes})
    # On transforme le résultat en un 'set' de bytes pour une recherche éclair
    return {row[0] for row in result.fetchall()}


# --- FONCTION DE CALCUL DU SCORE ---

def compute_tag_score(user_favorite_tags: Set[bytes], poll_tags_raw: bytes) -> float:
    """
    Compare les tags d'un sondage avec les tags préférés de l'utilisateur.
    """
    if not poll_tags_raw:
        return 0.0

    # MySQL GROUP_CONCAT renvoie une chaîne séparée par des virgules
    poll_tags = poll_tags_raw.split(b',')

    match_count = 0
    for tag in poll_tags:
        if tag in user_favorite_tags:
            match_count += 1

    # On donne 20 points de bonus par tag correspondant
    return float(match_count * 20)


# --- LE MOTEUR PRINCIPAL ---

async def get_personalized_feed(
        db: AsyncSession,
        user_id: UUID,
        limit: int,
        seen_ids: List[UUID]
) -> List[UUID]:
    # 1. Préparation des données utilisateur (Profil "Chaud")
    # On récupère ses catégories ET ses tags favoris en parallèle
    user_categories_task = db.execute(
        text("SELECT category_id FROM user_category WHERE user_id = :uid"),
        {"uid": user_id.bytes}
    )

    user_fav_tags = await get_user_favorite_tags(db, user_id)

    res_cats = await user_categories_task
    user_categories = {row[0] for row in res_cats.fetchall()}

    # 2. Récupération des sondages (avec Jointure pour les tags)
    query_str = """
                SELECT s.id, \
                       s.category_id, \
                       s.up, \
                       s.created_at,
                       GROUP_CONCAT(st.tag_id) as tags
                FROM surveys s
                         LEFT JOIN survey_tags st ON s.id = st.survey_id \
                """

    params = {}
    if seen_ids:
        query_str += " WHERE s.id NOT IN :seen"
        params["seen"] = [s.bytes for s in seen_ids]

    query_str += " GROUP BY s.id"

    surveys_query = await db.execute(text(query_str), params)
    all_surveys = surveys_query.fetchall()

    # 3. Boucle de Scoring
    scored_surveys = []
    now = datetime.now(timezone.utc)

    for s_id, s_cat_id, s_up, s_created_at, s_tags in all_surveys:
        score = 0.0

        # Signal 1 : Catégories (Choix conscients de l'user)
        if s_cat_id in user_categories:
            score += 100.0

        # Signal 2 : Tags (Comportement réel/inconscient de l'user)
        score += compute_tag_score(user_fav_tags, s_tags)

        # Signal 3 : Popularité
        score += 1.5 * float(s_up)

        # Signal 4 : Fraîcheur
        if s_created_at:
            if s_created_at.tzinfo is None:
                s_created_at = s_created_at.replace(tzinfo=timezone.utc)
            hours_old = (now - s_created_at).total_seconds() / 3600
            score += max(0, 30 - (hours_old * 0.5))

        scored_surveys.append((UUID(bytes=s_id), score))

    # 4. Tri et Limite
    scored_surveys.sort(key=lambda x: x[1], reverse=True)
    return [s[0] for s in scored_surveys[:limit]]