# pyrefly: ignore [missing-import]
import os
import sys

# Add parent directory of backend to path to allow backend.* imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Import routers
from backend.api.routes import auth, mood, aura, insights

app = FastAPI(
    title="Serene Web Platform API",
    description="Backend API for Serene mental wellness platform",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting handler
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(mood.router, prefix="/api/v1/mood", tags=["Mood"])
app.include_router(aura.router, prefix="/api/v1/aura", tags=["Aura"])
app.include_router(insights.router, prefix="/api/v1/insights", tags=["Insights"])

@app.get("/health")
def health_check():
    return {"status": "healthy"}

