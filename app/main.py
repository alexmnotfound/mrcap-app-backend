from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db, close_db
from app.middleware.auth import initialize_firebase
from app.routers import users, movements, accounts, funds
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MR Capitals Dashboard API",
    description="Backend API for MR Capitals Dashboard",
    version="1.0.0"
)

# CORS
# Configure CORS for production with specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.mrcapitals.com.ar",
        "http://app.mrcapitals.com.ar",  # For development/testing
        "http://localhost:3000",  # Local development
        "http://localhost:3001",  # Alternative local port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database and Firebase on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    initialize_firebase()
    logger.info("Application started")


@app.on_event("shutdown")
async def shutdown_event():
    close_db()
    logger.info("Application shutdown")


# Health check
@app.get("/health")
async def health_check():
    return {"status": "ok"}


# Include routers
app.include_router(users.router, prefix="/api")
app.include_router(movements.router, prefix="/api")
app.include_router(accounts.router, prefix="/api")
app.include_router(funds.router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )

