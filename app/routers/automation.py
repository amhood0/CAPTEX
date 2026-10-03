"""Phase 5 guest-local Ansible controls."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Environment
from app.routers.pages import render_template
from app.routers.virtualization import is_managed, managed_environment, require_same_origin
from app.services.automation_operations import manager

router = APIRouter(dependencies=[Depends(require_same_origin)])


def get_automation_manager():
    return manager


@router.get("/automation", response_class=HTMLResponse)
def automation_page(request: Request, db: Session = Depends(get_db)):
    return HTMLResponse(render_template(
        "automation.html", {"environment": managed_environment(db)}, request=request
    ))


@router.get("/api/automation/operation")
def operation(automation=Depends(get_automation_manager)):
    return automation.state()


@router.post("/api/environments/{environment_id}/automation/{action}", status_code=202)
def automation_action(
    environment_id: int,
    action: Literal["connectivity", "prepare", "validate"],
    db: Session = Depends(get_db),
    automation=Depends(get_automation_manager),
):
    environment = db.get(Environment, environment_id)
    if environment is None:
        raise HTTPException(404, "Environment not found")
    if not is_managed(environment.vagrant_path):
        raise HTTPException(400, "Ansible is limited to the approved Ubuntu VMware environment")
    return automation.submit(action, environment_id)
