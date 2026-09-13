"""
Environments API router
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Environment
from app.schemas import EnvironmentCreate, EnvironmentResponse, EnvironmentUpdate

router = APIRouter(prefix="/api/environments", tags=["environments"])


@router.get("", response_model=list[EnvironmentResponse])
def list_environments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List all environments"""
    return db.query(Environment).offset(skip).limit(limit).all()


@router.post("", response_model=EnvironmentResponse)
def create_environment(
    environment: EnvironmentCreate,
    db: Session = Depends(get_db)
):
    """Create a new environment"""
    # Check if name already exists
    existing = db.query(Environment).filter(Environment.name == environment.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Environment with this name already exists")
    
    db_environment = Environment(**environment.model_dump())
    db.add(db_environment)
    db.commit()
    db.refresh(db_environment)
    return db_environment


@router.get("/{environment_id}", response_model=EnvironmentResponse)
def get_environment(
    environment_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific environment"""
    environment = db.query(Environment).filter(Environment.id == environment_id).first()
    if not environment:
        raise HTTPException(status_code=404, detail="Environment not found")
    return environment


@router.put("/{environment_id}", response_model=EnvironmentResponse)
def update_environment(
    environment_id: int,
    environment: EnvironmentUpdate,
    db: Session = Depends(get_db)
):
    """Update an environment"""
    db_environment = db.query(Environment).filter(Environment.id == environment_id).first()
    if not db_environment:
        raise HTTPException(status_code=404, detail="Environment not found")
    
    # Check if new name is unique
    if environment.name:
        existing = db.query(Environment).filter(
            Environment.name == environment.name,
            Environment.id != environment_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Environment with this name already exists")
    
    update_data = environment.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_environment, key, value)
    
    db.add(db_environment)
    db.commit()
    db.refresh(db_environment)
    return db_environment


@router.delete("/{environment_id}")
def delete_environment(
    environment_id: int,
    db: Session = Depends(get_db)
):
    """Delete an environment"""
    db_environment = db.query(Environment).filter(Environment.id == environment_id).first()
    if not db_environment:
        raise HTTPException(status_code=404, detail="Environment not found")
    
    if db_environment.test_runs:
        raise HTTPException(status_code=409, detail="Cannot delete a record with run history")
    db.delete(db_environment)
    db.commit()
    return {"message": "Environment deleted successfully"}
