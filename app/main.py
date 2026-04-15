from fastapi import FastAPI, Depends, Header, HTTPException
from app.config import settings
from app.routers import feed

app = FastAPI(
    title="Askeet Recommender API",
    description="Service de scoring et recommandation pour les sondages",
    version="1.0.0"
)

async def verify_rust_token(x_api_key: str = Header(None)):
    if x_api_key != settings.API_SECRET_KEY:
        raise HTTPException(
            status_code=403,
            detail="Accès refusé : Clé API invalide ou manquante"
        )

#Inclusion des routes
app.include_router(
    feed.router,
    prefix="/v1",
    tags=["Recommendation"],
    # Décommente la ligne suivante pour activer la sécurité API Key :
    #dependencies=[Depends(verify_rust_token)]
)

# 4. Route de santé (Healthcheck)
@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "recommender-engine",
        "message": "En attente de requêtes du backend Rust"
    }