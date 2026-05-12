import random
import math
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Set, Tuple
from datetime import datetime, timezone


# --- 1. RÉCUPÉRATION DES CANDIDATS (STAGE 1 : RETRIEVAL) ---

async def get_candidates(db: AsyncSession, user_categories: Set[bytes], limit=200) -> List[bytes]:
    """Récupère rapidement un pool de candidats potentiels (Retrieval)."""
    # On utilise UNION pour mixer les sources de candidats
    query = text("""
        (SELECT id FROM surveys WHERE category_id IN :cats ORDER BY created_at DESC LIMIT 100)
        UNION
        (SELECT id FROM surveys ORDER BY up DESC LIMIT 50)
        UNION
        (SELECT id FROM surveys ORDER BY created_at DESC LIMIT 50)
    """)

    # Fallback si l'user n'a pas de catégories
    cats = list(user_categories) if user_categories else [b'\x00' * 16]
    result = await db.execute(query, {"cats": cats})
    return [row[0] for row in result.fetchall()]


async def get_user_favorite_tags(db: AsyncSession, user_id: UUID) -> Set[bytes]:
    """Analyse l'historique de l'utilisateur pour trouver ses tags favoris."""
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
    return {row[0] for row in result.fetchall()}


# --- 2. LOGIQUE DE SCORING DÉTAILLÉE (STAGE 2 : RANKING) ---

def compute_full_score(
        s_up: int,
        s_down: int,
        s_cat_id: bytes,
        user_categories: Set[bytes],
        user_fav_tags: Set[bytes],
        s_tags_raw: bytes,
        s_created_at: datetime,
        now: datetime
) -> Tuple[float, float]:
    # On commence avec un petit score de base (10) pour que même un
    # vieux sondage sans vote puisse exister
    score = 10.0
    tag_bonus = 0.0

    # A. Catégories (+100)
    if s_cat_id in user_categories:
        score += 100.0

    # B. Tags (+50 par match)
    if s_tags_raw:
        # GROUP_CONCAT peut renvoyer des bytes ou string selon le driver
        tags_str = s_tags_raw if isinstance(s_tags_raw, bytes) else s_tags_raw.encode()
        poll_tags = tags_str.split(b',')

        match_count = sum(1 for t in poll_tags if t in user_fav_tags)
        tag_bonus = float(match_count * 50)
        score += tag_bonus

    # C. Popularité (Engagement net)
    score += 0.5 * float(s_up or 0)
    score -= 0.5 * float(s_down or 0)

    # D. Fraîcheur (Time Decay Exponentiel)
    if s_created_at:
        if s_created_at.tzinfo is None:
            s_created_at = s_created_at.replace(tzinfo=timezone.utc)

        hours_old = (now - s_created_at).total_seconds() / 3600
        # Décroissance exponentielle : lambda = 0.01 (perte de ~1% de force par heure)
        decay = math.exp(-0.01 * hours_old)
        score *= decay

        # Bonus fixe pour la nouveauté absolue (< 24h)
        if hours_old < 24:
            score += 20.0

    return score, tag_bonus


# --- 3. MOTEUR DE RECOMMANDATION (L'ENTONNOIR) ---

async def get_personalized_feed(
        db: AsyncSession,
        user_id: UUID,
        limit: int,
        seen_ids: List[UUID]
) -> List[UUID]:
    now = datetime.now(timezone.utc)

    # 1. Chargement du profil utilisateur
    user_fav_tags = await get_user_favorite_tags(db, user_id)
    res_cats = await db.execute(
        text("SELECT category_id FROM user_category WHERE user_id = :uid"),
        {"uid": user_id.bytes}
    )
    user_categories = {row[0] for row in res_cats.fetchall()}

    # 2. Stage 1 : Retrieval (Récupération des IDs candidats)
    candidate_ids = await get_candidates(db, user_categories)

    # Filtrage des sondages déjà vus par l'utilisateur
    seen_bytes = {s.bytes for s in seen_ids}
    filtered_candidates = [c for c in candidate_ids if c not in seen_bytes]

    if not filtered_candidates:
        return []

    # 3. Stage 2 : Ranking (Scoring précis sur les candidats uniquement)
    query_str = """
                SELECT s.id, s.category_id, s.up, s.down, s.created_at, GROUP_CONCAT(st.tag_id) as tags
                FROM surveys s
                         LEFT JOIN survey_tags st ON s.id = st.survey_id
                WHERE s.id IN :cands
                GROUP BY s.id
                """
    res = await db.execute(text(query_str), {"cands": filtered_candidates})
    candidate_data = res.fetchall()

    scored_surveys = []
    for row in candidate_data:
        s_id, s_cat_id, s_up, s_down, s_created_at, s_tags = row

        score, score_tags = compute_full_score(
            s_up, s_down, s_cat_id, user_categories,
            user_fav_tags, s_tags, s_created_at, now
        )

        # Print de debug
        if score > 0:
            print(f"--- Scoring Survey {UUID(bytes=s_id)} ---")
            print(f" > Base (Catégorie): {'+100' if s_cat_id in user_categories else '0'}")
            print(f" > Bonus Tags: {score_tags}")
            print(f" > Score Final (avec decay): {score:.2f}")

        # --- CORRECTION : Indentation à l'intérieur de la boucle ---
        scored_surveys.append((UUID(bytes=s_id), score, s_cat_id))

    # Tri par score décroissant
    scored_surveys.sort(key=lambda x: x[1], reverse=True)

    # 4. Stage 3 : Anti-Bulle (Exploration)
    final_ids = []
    top_limit = int(limit * 0.8)  # 80% de pertinence

    # On prend les meilleurs scores
    final_ids.extend([s[0] for s in scored_surveys[:top_limit]])

    # On cherche des catégories différentes pour les 20% restants
    remaining = scored_surveys[top_limit:]
    discovery = [s[0] for s in remaining if s[2] not in user_categories]

    if len(discovery) < (limit - top_limit):
        others = [s[0] for s in remaining if s[0] not in discovery]
        random.shuffle(others)
        discovery.extend(others)

    random.shuffle(discovery)
    final_ids.extend(discovery[:(limit - top_limit)])

    return final_ids[:limit]