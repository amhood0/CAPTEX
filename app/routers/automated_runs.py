"""Automated test execution endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TestRun
from app.routers.virtualization import is_managed, require_same_origin
from app.routers.artifacts import get_artifact_store
from app.services.automated_runs import manager
from app.services.capability_execution import CapabilityExecutionService

router = APIRouter(dependencies=[Depends(require_same_origin)])


def get_automated_run_manager():
    return manager


@router.get("/api/automated-runs/operation")
def operation(automation=Depends(get_automated_run_manager)):
    return automation.state()


@router.post("/api/test-runs/{run_id}/execute", status_code=202)
def execute_run(run_id: int, db: Session = Depends(get_db), automation=Depends(get_automated_run_manager),
                artifacts=Depends(get_artifact_store)):
    run = db.get(TestRun, run_id)
    if run is None:
        raise HTTPException(404, "Test run not found")
    if run.status != "queued":
        raise HTTPException(409, "Only a queued run can be executed automatically")
    if not is_managed(run.environment.vagrant_path):
        raise HTTPException(400, "Automated testing requires the managed Ubuntu VMware environment")
    try:
        artifacts.resolve(run.capability_version.artifact_path)
        CapabilityExecutionService.argv(run.capability_version.execution_command)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    return automation.submit_run(run_id)
