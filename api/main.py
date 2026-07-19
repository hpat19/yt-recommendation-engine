"""
api/main.py

FastAPI application entry point. Wires the routes into an app instance;
run locally with:

    uvicorn api.main:app --reload
"""

from fastapi import FastAPI

from api.routes.videos import router

app = FastAPI(
    title="YouTube Recommendation Engine",
    description="Trending video analytics and content-based recommendations",
    version="0.1.0",
)

app.include_router(router)