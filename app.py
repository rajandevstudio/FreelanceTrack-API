from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings

def create_app() -> FastAPI:
    """
    Factory function to initialize the FastAPI application.
    """
    app = FastAPI(
        title="FreelanceTrack API",
        description="API for managing freelance projects, clients, and payments.",
        version="1.0.0",
    )

    # Configure CORS (Cross-Origin Resource Sharing)
    # This allows your frontend (e.g., React/Vue) to talk to this API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["Health"])
    async def health_check():
        """
        Endpoint to verify the API is running and check environment status.
        """
        return {
            "status": "healthy",
            "environment": settings.APP_ENV,
            "version": "1.0.0"
        }

    return app

app = create_app()
