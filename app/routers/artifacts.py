"""Capability artifact upload and management API."""
from pathlib import Path
import tempfile
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CapabilityVersion
from app.routers.virtualization import require_same_origin
from app.services.artifacts import ArtifactError, ArtifactStore, MAX_UPLOAD, store

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"], dependencies=[Depends(require_same_origin)])


def get_artifact_store():
    return store


@router.get("")
def list_artifacts(artifacts=Depends(get_artifact_store)):
    return artifacts.list()


@router.post("", status_code=201)
async def upload_artifact(request: Request, artifacts=Depends(get_artifact_store)):
    name = unquote(request.headers.get("x-captex-filename", ""))
    size = 0
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as output:
            temporary = Path(output.name)
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_UPLOAD:
                    raise HTTPException(413, "Capability ZIP exceeds 25 MiB")
                output.write(chunk)
        return artifacts.import_zip(temporary, name)
    except ArtifactError as error:
        raise HTTPException(400, str(error)) from error
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


@router.delete("/{artifact_id}")
def delete_artifact(artifact_id: str, db: Session = Depends(get_db), artifacts=Depends(get_artifact_store)):
    identifier = f"managed:{artifact_id}"
    if db.query(CapabilityVersion).filter(CapabilityVersion.artifact_path == identifier).first():
        raise HTTPException(409, "Artifact is used by a capability version")
    try:
        artifacts.delete(identifier)
    except ArtifactError as error:
        raise HTTPException(404, str(error)) from error
    return {"message": "Artifact deleted"}
