import asyncio
import random
from faker import Faker
import uuid
from sqlalchemy import text
from app.infrastructure.db import AsyncSessionLocal

fake = Faker('fr_FR')

async def seed_data():
    async with AsyncSessionLocal() as session:
        print("Nettoyage des anciennes données")
        await session.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        tables = ["surveys", "users", "categories", "user_category", "tags", "survey_tags", "votes"]
        for table in tables:
            await session.execute(text(f"TRUNCATE {table};"))
        await session.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))

        print("Création des catégories...")
        categories = ["Sport", "Tech", "Cuisine", "Politique", "Gaming", "Musique", "Voyage", "Cinéma"]
        category_ids = []
        for cat in categories:
            cat_id = uuid.uuid4().bytes
            await session.execute(
                text("INSERT INTO categories (id, name) VALUES (:id, :c)"), {"id": cat_id, "c": cat}
            )
            #on récupère l'ID via lastrowid
            category_ids.append(cat_id)

        print("Création des utilisateurs...")
        user_ids = []
        for _ in range(20):
            u_id = uuid.uuid4().bytes
            await session.execute(text(
                "INSERT INTO users (id, first_name, last_name, pseudo, email, password) "
                "VALUES (:id, :fn, :ln, :p, :e, :pa)"),
                {
                    "id": u_id,
                    "fn": fake.first_name(),
                    "ln": fake.last_name(),
                    "p": fake.user_name(),
                    "e": fake.email(),
                    "pa": "password123"
                }
            )
            user_ids.append(u_id)

        print("🏷️ Création des tags...")
        tags_pool = ["#fun", "#vintage", "#actu", "#debat", "#insolite", "#manger", "#sportif", "#gaming"]
        tag_ids = []
        for t_name in tags_pool:
            t_id = uuid.uuid4().bytes
            await session.execute(text("INSERT INTO tags (id, name) VALUES (:id, :n)"), {"id": t_id, "n": t_name})
            tag_ids.append(t_id)

        print("Remplissage des intérêts (user_category)...")
        for u_id in user_ids:
            # On donne entre 1 et 3 intérêts par utilisateur
            chosen_cats = random.sample(category_ids, k=random.randint(1, 3))
            for c_id in chosen_cats:
                uc_id = uuid.uuid4().bytes
                await session.execute(
                    text("INSERT INTO user_category (id, user_id, category_id) VALUES (:id, :uid, :cid)"),
                    {"id": uc_id, "uid": u_id, "cid": c_id}
                )

        print("📊 Création des sondages...")
        survey_ids = []
        for _ in range(50):
            s_id = uuid.uuid4().bytes
            await session.execute(text(
                "INSERT INTO surveys (id, creator_id, title, up, category_id, created_at) "
                "VALUES (:id ,:ci, :t, :up, :cati, NOW())"),
                {
                    "id": s_id, "ci": random.choice(user_ids), "t": fake.sentence() + " ?",
                    "up": random.randint(5, 1000), "cati": random.choice(category_ids)
                }
            )
            survey_ids.append(s_id)

            # Lier 1 à 3 tags par sondage
            chosen_tags = random.sample(tag_ids, k=random.randint(1, 3))
            for t_id in chosen_tags:
                await session.execute(text(
                    "INSERT INTO survey_tags (survey_id, tag_id) VALUES (:sid, :tid)"),
                    {"sid": s_id, "tid": t_id}
                )

        print("🗳️ Génération des votes (pour l'algo)...")
        for u_id in user_ids:
            # Chaque user vote "up" sur 5 sondages au hasard
            voted_surveys = random.sample(survey_ids, k=5)
            for s_id in voted_surveys:
                await session.execute(text(
                    "INSERT INTO votes (id, user_id, poll_id, type) VALUES (:id, :uid, :pid, 'up')"),
                    {"id": uuid.uuid4().bytes, "uid": u_id, "pid": s_id}
                )

        await session.commit()
        print("Base de données locale peuplée avec succès !")

if __name__ == "__main__":
    try:
        asyncio.run(seed_data())
    except Exception as e:
        print(f"Erreur lors du seeding : {e}")