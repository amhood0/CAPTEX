"""
Main FastAPI application
"""
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pathlib import Path
from app.config import IS_FROZEN, settings
from app.runtime import setup_complete
from app.services.vm_operations import manager as vm_manager
from app.services.automation_operations import manager as automation_manager
from app.services.automated_runs import manager as automated_run_manager
from app.routers import artifacts, automated_runs, automation, capabilities, environments, test_plans, test_runs, pages, forms, virtualization

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
app.include_router(virtualization.router, tags=["virtualization"])
app.include_router(automation.router, tags=["automation"])
app.include_router(automated_runs.router, tags=["automated-runs"])
app.include_router(artifacts.router, tags=["artifacts"])
app.include_router(forms.router, tags=["forms"])
app.include_router(pages.router, tags=["pages"])
app.include_router(capabilities.router, tags=["capabilities"])
app.include_router(environments.router, tags=["environments"])
app.include_router(test_plans.router, tags=["test_plans"])
app.include_router(test_runs.router, tags=["test_runs"])

# Root redirect
@app.get("/", include_in_schema=False)
def root():
    """Send packaged first launches through readiness setup."""
    return RedirectResponse(url="/setup" if IS_FROZEN and not setup_complete() else "/dashboard")

@app.get("/health", tags=["health"])
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "app": settings.APP_NAME}


@app.post("/api/application/exit", include_in_schema=False)
def exit_application(request: Request, background_tasks: BackgroundTasks):
    """Gracefully stop the packaged local server when no operation is active."""
    origin = request.headers.get("origin")
    if request.headers.get("sec-fetch-site") == "cross-site" or (origin and origin != str(request.base_url).rstrip("/")):
        raise HTTPException(403, "Exit must be requested from this application's page")
    operations = (
        ("virtual machine", vm_manager.state()),
        ("Ansible", automation_manager.state()),
        ("automated test", automated_run_manager.state()),
    )
    active = [name for name, operation in operations if operation.get("status") not in
              {None, "idle", "succeeded", "failed", "interrupted", "error"}]
    if active:
        raise HTTPException(409, f"Cannot exit while a {active[0]} operation is active")
    callback = getattr(request.app.state, "request_shutdown", None)
    if callback is None:
        raise HTTPException(409, "Exit CAPTEX is available from the packaged application")
    background_tasks.add_task(callback)
    return {"message": "CAPTEX is shutting down. Your data has been saved."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
