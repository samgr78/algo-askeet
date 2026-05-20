from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

# 1. Création du moteur de connexion
# Pool volontairement petit : MySQL mutualisé Hostinger plafonne très bas
# max_user_connections. pool_pre_ping teste la connexion avant usage et
# pool_recycle la recycle avant le wait_timeout court de Hostinger
# (évite "Lost connection / Connection reset by peer").
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=3,
    max_overflow=2,
    pool_recycle=180,
    echo=False  # Mets True pour voir les requêtes SQL dans la console en dev
)

# 2. Créateur de session (le "tunnel" pour tes requêtes)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 3. Base pour les modèles (si tu veux mapper tes tables MySQL en objets Python)
Base = declarative_base()

# 4. Dependency Injection pour FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()