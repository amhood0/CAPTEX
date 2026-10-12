"""Managed ZIP imports and bundled capability artifact discovery."""
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
from uuid import uuid4
import zipfile

from app.config import BASE_DIR, settings

MAX_UPLOAD = 25 * 1024 * 1024
MAX_EXTRACTED = 100 * 1024 * 1024
MAX_ENTRIES = 1000
BUNDLED_ROOT = (BASE_DIR / "capability_artifacts").resolve()


class ArtifactError(ValueError):
    pass


class ArtifactStore:
    def __init__(self, root=None):
        self.root = Path(root or settings.DATA_DIR / "artifacts").resolve()

    def list(self):
        bundled = [{"id": f"bundled:{item.name}", "name": item.name, "source": "bundled"}
                   for item in sorted(BUNDLED_ROOT.iterdir()) if item.is_dir()]
        managed = []
        if self.root.exists():
            for item in sorted(self.root.iterdir()):
                metadata = item / ".captex-artifact.json"
                if item.is_dir() and metadata.is_file():
                    try:
                        name = json.loads(metadata.read_text(encoding="utf-8"))["name"]
                    except (OSError, ValueError, KeyError):
                        name = item.name
                    managed.append({"id": f"managed:{item.name}", "name": name, "source": "uploaded"})
        return bundled + managed

    def resolve(self, identifier):
        prefix, separator, value = (identifier or "").partition(":")
        if not separator or not value or "/" in value or "\\" in value or value in {".", ".."}:
            raise ArtifactError("Select a managed or bundled capability artifact")
        root = BUNDLED_ROOT if prefix == "bundled" else self.root if prefix == "managed" else None
        if root is None:
            raise ArtifactError("Unknown capability artifact source")
        candidate = (root / value).resolve()
        if root not in candidate.parents or not candidate.is_dir():
            raise ArtifactError("Capability artifact is unavailable")
        return candidate

    def import_zip(self, archive_path, original_name):
        if not original_name.lower().endswith(".zip"):
            raise ArtifactError("Capability uploads must be ZIP archives")
        artifact_id = uuid4().hex
        self.root.mkdir(parents=True, exist_ok=True)
        destination = self.root / artifact_id
        temporary = self.root / f".{artifact_id}.tmp"
        completed = False
        try:
            with zipfile.ZipFile(archive_path) as archive:
                entries = archive.infolist()
                if not entries or len(entries) > MAX_ENTRIES:
                    raise ArtifactError(f"Archive must contain 1 to {MAX_ENTRIES} entries")
                if sum(item.file_size for item in entries) > MAX_EXTRACTED:
                    raise ArtifactError("Expanded capability exceeds 100 MiB")
                normalized = set()
                for item in entries:
                    path = PurePosixPath(item.filename.replace("\\", "/"))
                    mode = item.external_attr >> 16
                    key = tuple(part.casefold() for part in path.parts)
                    if (path.is_absolute() or ".." in path.parts or any(":" in part for part in path.parts)
                            or stat.S_ISLNK(mode) or key in normalized):
                        raise ArtifactError("Archive contains an unsafe path or symbolic link")
                    normalized.add(key)
                extracted = 0
                for item in entries:
                    relative = PurePosixPath(item.filename.replace("\\", "/"))
                    target = temporary.joinpath(*relative.parts)
                    if item.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(item) as source, target.open("wb") as output:
                        while chunk := source.read(1024 * 1024):
                            extracted += len(chunk)
                            if extracted > MAX_EXTRACTED:
                                raise ArtifactError("Expanded capability exceeds 100 MiB")
                            output.write(chunk)
            children = [item for item in temporary.iterdir() if item.name != "__MACOSX"]
            if not children:
                raise ArtifactError("Archive contains no capability files")
            content = children[0] if len(children) == 1 and children[0].is_dir() else temporary
            destination.mkdir()
            for item in content.iterdir():
                shutil.move(str(item), destination / item.name)
            (destination / ".captex-artifact.json").write_text(
                json.dumps({"name": Path(original_name).stem}), encoding="utf-8")
            completed = True
            return {"id": f"managed:{artifact_id}", "name": Path(original_name).stem, "source": "uploaded"}
        except zipfile.BadZipFile as error:
            raise ArtifactError("Uploaded file is not a valid ZIP archive") from error
        except (OSError, RuntimeError) as error:
            raise ArtifactError(f"Capability archive could not be extracted: {error}") from error
        finally:
            shutil.rmtree(temporary, ignore_errors=True)
            if not completed:
                shutil.rmtree(destination, ignore_errors=True)

    def delete(self, identifier):
        path = self.resolve(identifier)
        if not identifier.startswith("managed:"):
            raise ArtifactError("Bundled artifacts cannot be deleted")
        shutil.rmtree(path)


store = ArtifactStore()
