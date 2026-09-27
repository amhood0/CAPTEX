"""API and page for the single managed Ubuntu VMware environment."""
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.config import BASE_DIR
from app.database import get_db
from app.models import Environment
from app.routers.pages import render_template
from app.services.vagrant import TEMPLATE, BOX, BOX_VERSION
from app.services.vm_operations import manager

def require_same_origin(request: Request):
    """Prevent other browser sites from triggering local VM commands."""
    if request.method == "POST":
        origin = request.headers.get("origin")
        if request.headers.get("sec-fetch-site") == "cross-site" or (origin and origin != str(request.base_url).rstrip("/")):
            raise HTTPException(403, "VM controls must be used from this application's page")


router = APIRouter(dependencies=[Depends(require_same_origin)])


def get_vm_manager():
    return manager


def is_managed(path):
    if not path:
        return False
    value = Path(path)
    return (value if value.is_absolute() else BASE_DIR / value).resolve() == TEMPLATE.resolve()


def managed_environment(db):
    return next((env for env in db.query(Environment).order_by(Environment.id) if is_managed(env.vagrant_path)), None)


@router.get("/virtualization", response_class=HTMLResponse)
def virtualization_page(request: Request, db: Session = Depends(get_db)):
    return HTMLResponse(render_template("virtualization.html", dict(environment=managed_environment(db), box=BOX,
        box_version=BOX_VERSION), request=request))


@router.post("/api/virtualization/environment")
def register_environment(db: Session = Depends(get_db)):
    environment = managed_environment(db)
    if environment is None:
        name = "CAPTEX Ubuntu 24.04 VM"
        if db.query(Environment).filter_by(name=name).first():
            raise HTTPException(409, "An environment with this name exists. Rename it before registering the managed VM.")
        environment = Environment(name=name, os="Ubuntu", os_version="24.04", architecture="x86_64",
            vagrant_path="environments/ubuntu24", description="Single Vagrant-managed VMware test environment")
        db.add(environment)
        db.commit()
        db.refresh(environment)
    return {"id": environment.id, "name": environment.name}


@router.get("/api/virtualization/operation")
def operation(vm=Depends(get_vm_manager)):
    return vm.state()


@router.post("/api/virtualization/check", status_code=202)
def check_prerequisites(vm=Depends(get_vm_manager)):
    return vm.submit("check")


@router.post("/api/environments/{environment_id}/vm/{action}", status_code=202)
def vm_action(environment_id: int, action: Literal["status", "start", "stop"], db: Session = Depends(get_db), vm=Depends(get_vm_manager)):
    environment = db.get(Environment, environment_id)
    if environment is None:
        raise HTTPException(404, "Environment not found")
    if not is_managed(environment.vagrant_path):
        raise HTTPException(400, "This environment is not mapped to the approved Ubuntu VMware template")
    return vm.submit(action, environment_id)
