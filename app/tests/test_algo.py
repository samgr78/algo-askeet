import asyncio
from sqlalchemy import text
from app.infrastructure.db import AsyncSessionLocal
from app.scoring.engine import get_personalized_feed
from uuid import UUID


async def verify_algo(user_uuid_str):
    user_id = UUID(user_uuid_str)

    async with AsyncSessionLocal() as db:
        # 1. On récupère les recos de l'algo
        recos = await get_personalized_feed(db, user_id, limit=10, seen_ids=[])

        print(f"\n Vérification pour l'user {user_uuid_str}")

        for i, poll_id in enumerate(recos):
            # 2. Pour chaque reco, on regarde sa catégorie et ses tags en SQL
            res = await db.execute(text("""
                                        SELECT s.title, c.name as cat_name, GROUP_CONCAT(t.name) as tag_names
                                        FROM surveys s
                                                 JOIN categories c ON s.category_id = c.id
                                                 LEFT JOIN survey_tags st ON s.id = st.survey_id
                                                 LEFT JOIN tags t ON st.tag_id = t.id
                                        WHERE s.id = :pid
                                        GROUP BY s.id
                                        """), {"pid": poll_id.bytes})

            row = res.fetchone()
            print(f"Position {i + 1}: {row[0]}")
            print(f"   Category: {row[1]} | Tags: {row[2]}")


if __name__ == "__main__":
    # Mettre un id de tests
    u_id = "12d42810-5fd4-414f-8110-af806d02afdc"
    asyncio.run(verify_algo(u_id))