"""
Capabilities API router
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Capability, CapabilityVersion
from app.schemas import CapabilityCreate, CapabilityResponse, CapabilityUpdate, CapabilityVersionCreate, CapabilityVersionResponse, CapabilityVersionUpdate

router = APIRouter(prefix="/api/capabilities", tags=["capabilities"])


@router.get("", response_model=list[CapabilityResponse])
def list_capabilities(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List all capabilities"""
    return db.query(Capability).offset(skip).limit(limit).all()


@router.post("", response_model=CapabilityResponse)
def create_capability(
    capability: CapabilityCreate,
    db: Session = Depends(get_db)
):
    """Create a new capability"""
    # Check if name already exists
    existing = db.query(Capability).filter(Capability.name == capability.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Capability with this name already exists")
    
    db_capability = Capability(**capability.model_dump())
    db.add(db_capability)
    db.commit()
    db.refresh(db_capability)
    return db_capability


@router.get("/{capability_id}", response_model=CapabilityResponse)
def get_capability(
    capability_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific capability"""
    capability = db.query(Capability).filter(Capability.id == capability_id).first()
    if not capability:
        raise HTTPException(status_code=404, detail="Capability not found")
    return capability


@router.put("/{capability_id}", response_model=CapabilityResponse)
def update_capability(
    capability_id: int,
    capability: CapabilityUpdate,
    db: Session = Depends(get_db)
):
    """Update a capability"""
    db_capability = db.query(Capability).filter(Capability.id == capability_id).first()
    if not db_capability:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    # Check if new name is unique
    if capability.name:
        existing = db.query(Capability).filter(
            Capability.name == capability.name,
            Capability.id != capability_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Capability with this name already exists")
    
    update_data = capability.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_capability, key, value)
    
    db.add(db_capability)
    db.commit()
    db.refresh(db_capability)
    return db_capability


@router.delete("/{capability_id}")
def delete_capability(
    capability_id: int,
    db: Session = Depends(get_db)
):
    """Delete a capability"""
    db_capability = db.query(Capability).filter(Capability.id == capability_id).first()
    if not db_capability:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    if any(v.test_runs for v in db_capability.versions) or any(p.test_runs for p in db_capability.test_plans):
        raise HTTPException(status_code=409, detail="Cannot delete a capability with run history")
    db.delete(db_capability)
    db.commit()
    return {"message": "Capability deleted successfully"}


# ============================================================================
# CapabilityVersion endpoints
# ============================================================================

@router.get("/{capability_id}/versions", response_model=list[CapabilityVersionResponse])
def list_versions(
    capability_id: int,
    db: Session = Depends(get_db)
):
    """List all versions for a capability"""
    # Check if capability exists
    capability = db.query(Capability).filter(Capability.id == capability_id).first()
    if not capability:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    return db.query(CapabilityVersion).filter(
        CapabilityVersion.capability_id == capability_id
    ).all()


@router.post("/{capability_id}/versions", response_model=CapabilityVersionResponse)
def create_version(
    capability_id: int,
    version: CapabilityVersionCreate,
    db: Session = Depends(get_db)
):
    """Create a new capability version"""
    # Check if capability exists
    capability = db.query(Capability).filter(Capability.id == capability_id).first()
    if not capability:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    if version.capability_id != capability_id:
        raise HTTPException(status_code=400, detail="Capability ID mismatch")

    # Validate version uniqueness per capability
    existing = db.query(CapabilityVersion).filter(
        CapabilityVersion.capability_id == capability_id,
        CapabilityVersion.version == version.version
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Version already exists for this capability")
    
    db_version = CapabilityVersion(capability_id=capability_id, **version.model_dump(exclude={"capability_id"}))
    db.add(db_version)
    db.commit()
    db.refresh(db_version)
    return db_version


@router.get("/{capability_id}/versions/{version_id}", response_model=CapabilityVersionResponse)
def get_version(
    capability_id: int,
    version_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific version"""
    version = db.query(CapabilityVersion).filter(
        CapabilityVersion.id == version_id,
        CapabilityVersion.capability_id == capability_id
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return version


@router.put("/{capability_id}/versions/{version_id}", response_model=CapabilityVersionResponse)
def update_version(
    capability_id: int,
    version_id: int,
    version: CapabilityVersionUpdate,
    db: Session = Depends(get_db)
):
    """Update a capability version"""
    db_version = db.query(CapabilityVersion).filter(
        CapabilityVersion.id == version_id,
        CapabilityVersion.capability_id == capability_id
    ).first()
    if not db_version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    if version.version is not None:
        existing = db.query(CapabilityVersion).filter(
            CapabilityVersion.capability_id == capability_id,
            CapabilityVersion.version == version.version,
            CapabilityVersion.id != version_id,
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Version already exists for this capability")
    for key, value in version.model_dump(exclude_unset=True).items():
        setattr(db_version, key, value)
    
    db.add(db_version)
    db.commit()
    db.refresh(db_version)
    return db_version


@router.delete("/{capability_id}/versions/{version_id}")
def delete_version(
    capability_id: int,
    version_id: int,
    db: Session = Depends(get_db)
):
    """Delete a capability version"""
    db_version = db.query(CapabilityVersion).filter(
        CapabilityVersion.id == version_id,
        CapabilityVersion.capability_id == capability_id
    ).first()
    if not db_version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    if db_version.test_runs:
        raise HTTPException(status_code=409, detail="Cannot delete a version with run history")
    db.delete(db_version)
    db.commit()
    return {"message": "Version deleted successfully"}
