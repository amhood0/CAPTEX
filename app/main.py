"""
Main FastAPI application
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pathlib import Path
from app.config import settings
from app.routers import capabilities, environments, test_plans, test_runs, pages, forms

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="A platform for managing and executing capability tests"
)

from app.errors import register_error_handlers
register_error_handlers(app)

# Mount static files
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# Include routers
app.include_router(forms.router, tags=["forms"])
app.include_router(pages.router, tags=["pages"])
app.include_router(capabilities.router, tags=["capabilities"])
app.include_router(environments.router, tags=["environments"])
app.include_router(test_plans.router, tags=["test_plans"])
app.include_router(test_runs.router, tags=["test_runs"])

# Root redirect
@app.get("/", include_in_schema=False)
def root():
    """Redirect to dashboard"""
    return RedirectResponse(url="/dashboard")

@app.get("/health", tags=["health"])
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "app": settings.APP_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
