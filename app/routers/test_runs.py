"""
Test Runs API router
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.services.manual_runs import ensure_editable, snapshot_cases, change_status
from typing import Literal
from app.database import get_db
from app.models import (
    TestRun, CapabilityVersion, TestPlan, Environment,
    TestResult, TestCase
)
from app.schemas import (
    TestRunCreate, TestRunResponse,
    TestResultCreate, TestResultResponse, TestResultUpdate
)

from app.services.history import history_query

router = APIRouter(prefix="/api", tags=["test_runs"])


# ============================================================================
# TestRun endpoints
# ============================================================================

@router.get("/test-runs", response_model=list[TestRunResponse])
def list_test_runs(
    q: str = "",
    status: str = "",
    overall_result: str = "",
    capability_id: str = "",
    environment_id: str = "",
    date_from: str = "",
    date_to: str = "",
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List all test runs"""
    return history_query(db, q, status, overall_result, capability_id, environment_id, date_from, date_to).offset(skip).limit(limit).all()


@router.post("/test-runs", response_model=TestRunResponse)
def create_test_run(
    test_run: TestRunCreate,
    db: Session = Depends(get_db)
):
    """Create a new test run"""
    # Validate all foreign keys exist
    capability_version = db.query(CapabilityVersion).filter(
        CapabilityVersion.id == test_run.capability_version_id
    ).first()
    if not capability_version:
        raise HTTPException(status_code=404, detail="Capability version not found")
    
    test_plan = db.query(TestPlan).filter(TestPlan.id == test_run.test_plan_id).first()
    if not test_plan:
        raise HTTPException(status_code=404, detail="Test plan not found")
    
    environment = db.query(Environment).filter(Environment.id == test_run.environment_id).first()
    if not environment:
        raise HTTPException(status_code=404, detail="Environment not found")
    
    if capability_version.capability_id != test_plan.capability_id:
        raise HTTPException(status_code=400, detail="Version and plan must belong to the same capability")
    if not capability_version.capability.active or not test_plan.active:
        raise HTTPException(400, "Choose an active capability and test plan")
    if not any(case.enabled for case in test_plan.test_cases):
        raise HTTPException(400, "The plan must contain at least one enabled test case")
    db_run = TestRun(**test_run.model_dump())
    snapshot_cases(db_run, test_plan.test_cases)
    db.add(db_run)
    db.commit()
    db.refresh(db_run)
    return db_run


@router.get("/test-runs/{test_run_id}", response_model=TestRunResponse)
def get_test_run(
    test_run_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific test run"""
    test_run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")
    return test_run


@router.put("/test-runs/{test_run_id}", response_model=TestRunResponse)
def update_test_run(
    test_run_id: int,
    status: Literal["queued", "provisioning", "configuring", "running", "collecting_results", "cleaning_up", "completed", "failed"] = None,
    overall_result: Literal["PASS", "FAIL", "ERROR", "CANCELLED"] = None,
    db: Session = Depends(get_db)
):
    """Update test run status and result"""
    db_run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
    if not db_run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    if overall_result is not None:
        raise HTTPException(400, "Overall result is calculated when the run is completed")
    if status:
        change_status(db_run, status)

    db.add(db_run)
    db.commit()
    db.refresh(db_run)
    return db_run


@router.delete("/test-runs/{test_run_id}")
def delete_test_run(
    test_run_id: int,
    db: Session = Depends(get_db)
):
    """Delete a test run"""
    db_run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
    if not db_run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    db.delete(db_run)
    db.commit()
    return {"message": "Test run deleted successfully"}


# ============================================================================
# TestResult endpoints
# ============================================================================

@router.get("/test-runs/{test_run_id}/results", response_model=list[TestResultResponse])
def list_test_results(
    test_run_id: int,
    db: Session = Depends(get_db)
):
    """List all results for a test run"""
    # Check if test run exists
    test_run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    return db.query(TestResult).filter(TestResult.test_run_id == test_run_id).all()


@router.post("/test-runs/{test_run_id}/results", response_model=TestResultResponse)
def create_test_result(
    test_run_id: int,
    result: TestResultCreate,
    db: Session = Depends(get_db)
):
    """Create a new test result"""
    # Check if test run exists
    test_run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    # Check if test case exists
    test_case = db.query(TestCase).filter(TestCase.id == result.test_case_id).first()
    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")
    
    # Ensure test_run_id matches
    if result.test_run_id != test_run_id:
        raise HTTPException(status_code=400, detail="Test run ID mismatch")
    
    if test_case.test_plan_id != test_run.test_plan_id:
        raise HTTPException(status_code=400, detail="Test case must belong to the run plan")
    ensure_editable(test_run)
    existing = db.query(TestResult).filter_by(test_run_id=test_run_id, test_case_id=result.test_case_id).first()
    if existing:
        if existing.status != "PENDING":
            raise HTTPException(409, "A result already exists; edit it instead")
        db_result = existing
        for key, value in result.model_dump(exclude_unset=True, exclude={"test_run_id", "test_case_id", "expected_result"}).items():
            setattr(db_result, key, value)
    else:
        raise HTTPException(400, "This case was not included when the run was created")
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result


@router.get("/test-results/{result_id}", response_model=TestResultResponse)
def get_test_result(
    result_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific test result"""
    result = db.query(TestResult).filter(TestResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Test result not found")
    return result


@router.put("/test-results/{result_id}", response_model=TestResultResponse)
def update_test_result(
    result_id: int,
    result: TestResultUpdate,
    db: Session = Depends(get_db)
):
    """Update a test result"""
    db_result = db.query(TestResult).filter(TestResult.id == result_id).first()
    if not db_result:
        raise HTTPException(status_code=404, detail="Test result not found")
    
    ensure_editable(db_result.test_run)
    update_data = result.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_result, key, value)
    
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result


@router.delete("/test-results/{result_id}")
def delete_test_result(
    result_id: int,
    db: Session = Depends(get_db)
):
    """Delete a test result"""
    db_result = db.query(TestResult).filter(TestResult.id == result_id).first()
    if not db_result:
        raise HTTPException(status_code=404, detail="Test result not found")
    
    ensure_editable(db_result.test_run)
    db_result.status = "PENDING"
    for field in ("actual_result", "stdout", "stderr", "exit_code", "duration", "notes"):
        setattr(db_result, field, None)
    db.commit()
    return {"message": "Result cleared; the case remains in the run"}
