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
        # décommenter pour repartir de zéro à chaque fois
        await session.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        await session.execute(text("TRUNCATE surveys; TRUNCATE users; TRUNCATE categories; TRUNCATE user_category;"))
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

        print("Création des sondages (Surveys)...")
        for _ in range(50):
            s_id = uuid.uuid4().bytes
            await session.execute(text(
                "INSERT INTO surveys (id, creator_id, title, category_id) VALUES (:id ,:ci, :t, :cati)"),
                {
                    "id": s_id,
                    "ci": random.choice(user_ids),
                    "t": fake.sentence(nb_words=6).replace(".", "") + " ?",
                    "cati": random.choice(category_ids),
                }
            )

        await session.commit()
        print("Base de données locale peuplée avec succès !")

if __name__ == "__main__":
    try:
        asyncio.run(seed_data())
    except Exception as e:
        print(f"Erreur lors du seeding : {e}")