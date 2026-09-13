"""
Test Plans API router
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Capability, TestPlan, TestCase
from app.schemas import (
    TestPlanCreate, TestPlanResponse, TestPlanUpdate,
    TestCaseCreate, TestCaseResponse, TestCaseUpdate
)

router = APIRouter(prefix="/api", tags=["test_plans"])


# ============================================================================
# TestPlan endpoints
# ============================================================================

@router.get("/test-plans", response_model=list[TestPlanResponse])
def list_test_plans(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List all test plans"""
    return db.query(TestPlan).offset(skip).limit(limit).all()


@router.post("/test-plans", response_model=TestPlanResponse)
def create_test_plan(
    test_plan: TestPlanCreate,
    db: Session = Depends(get_db)
):
    """Create a new test plan"""
    # Check if capability exists
    capability = db.query(Capability).filter(Capability.id == test_plan.capability_id).first()
    if not capability:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    db_plan = TestPlan(**test_plan.model_dump())
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    return db_plan


@router.get("/test-plans/{test_plan_id}", response_model=TestPlanResponse)
def get_test_plan(
    test_plan_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific test plan"""
    test_plan = db.query(TestPlan).filter(TestPlan.id == test_plan_id).first()
    if not test_plan:
        raise HTTPException(status_code=404, detail="Test plan not found")
    return test_plan


@router.put("/test-plans/{test_plan_id}", response_model=TestPlanResponse)
def update_test_plan(
    test_plan_id: int,
    test_plan: TestPlanUpdate,
    db: Session = Depends(get_db)
):
    """Update a test plan"""
    db_plan = db.query(TestPlan).filter(TestPlan.id == test_plan_id).first()
    if not db_plan:
        raise HTTPException(status_code=404, detail="Test plan not found")
    
    update_data = test_plan.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_plan, key, value)
    
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    return db_plan


@router.delete("/test-plans/{test_plan_id}")
def delete_test_plan(
    test_plan_id: int,
    db: Session = Depends(get_db)
):
    """Delete a test plan"""
    db_plan = db.query(TestPlan).filter(TestPlan.id == test_plan_id).first()
    if not db_plan:
        raise HTTPException(status_code=404, detail="Test plan not found")
    
    if db_plan.test_runs:
        raise HTTPException(status_code=409, detail="Cannot delete a record with run history")
    db.delete(db_plan)
    db.commit()
    return {"message": "Test plan deleted successfully"}


# ============================================================================
# TestCase endpoints
# ============================================================================

@router.get("/test-plans/{test_plan_id}/test-cases", response_model=list[TestCaseResponse])
def list_test_cases(
    test_plan_id: int,
    db: Session = Depends(get_db)
):
    """List all test cases for a test plan"""
    # Check if test plan exists
    test_plan = db.query(TestPlan).filter(TestPlan.id == test_plan_id).first()
    if not test_plan:
        raise HTTPException(status_code=404, detail="Test plan not found")
    
    return db.query(TestCase).filter(TestCase.test_plan_id == test_plan_id).all()


@router.post("/test-plans/{test_plan_id}/test-cases", response_model=TestCaseResponse)
def create_test_case(
    test_plan_id: int,
    test_case: TestCaseCreate,
    db: Session = Depends(get_db)
):
    """Create a new test case"""
    # Check if test plan exists
    test_plan = db.query(TestPlan).filter(TestPlan.id == test_plan_id).first()
    if not test_plan:
        raise HTTPException(status_code=404, detail="Test plan not found")
    
    # Ensure test_plan_id matches
    if test_case.test_plan_id != test_plan_id:
        raise HTTPException(status_code=400, detail="Test plan ID mismatch")
    
    db_case = TestCase(**test_case.model_dump())
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case


@router.get("/test-cases/{test_case_id}", response_model=TestCaseResponse)
def get_test_case(
    test_case_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific test case"""
    test_case = db.query(TestCase).filter(TestCase.id == test_case_id).first()
    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")
    return test_case


@router.put("/test-cases/{test_case_id}", response_model=TestCaseResponse)
def update_test_case(
    test_case_id: int,
    test_case: TestCaseUpdate,
    db: Session = Depends(get_db)
):
    """Update a test case"""
    db_case = db.query(TestCase).filter(TestCase.id == test_case_id).first()
    if not db_case:
        raise HTTPException(status_code=404, detail="Test case not found")
    
    update_data = test_case.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_case, key, value)
    
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case


@router.delete("/test-cases/{test_case_id}")
def delete_test_case(
    test_case_id: int,
    db: Session = Depends(get_db)
):
    """Delete a test case"""
    db_case = db.query(TestCase).filter(TestCase.id == test_case_id).first()
    if not db_case:
        raise HTTPException(status_code=404, detail="Test case not found")
    
    if db_case.test_results:
        raise HTTPException(status_code=409, detail="Cannot delete a record with run history")
    db.delete(db_case)
    db.commit()
    return {"message": "Test case deleted successfully"}
