"""Initialize writable state and packaged CAPTEX-owned runtime resources."""
from pathlib import Path
import shutil

from app.config import BASE_DIR, IS_FROZEN, MANAGED_ROOT, settings

MANAGED_ENVIRONMENT_NAME = "CAPTEX Ubuntu 24.04 VM"
MANAGED_ENVIRONMENT_PATH = "environments/ubuntu24"


def register_managed_environment(db):
    """Create the one CAPTEX-managed environment idempotently."""
    from app.models import Environment
    environment = db.query(Environment).filter_by(vagrant_path=MANAGED_ENVIRONMENT_PATH).first()
    if environment is not None:
        return environment
    name = MANAGED_ENVIRONMENT_NAME
    suffix = 2
    while db.query(Environment).filter_by(name=name).first() is not None:
        name = f"{MANAGED_ENVIRONMENT_NAME} ({suffix})"
        suffix += 1
    environment = Environment(name=name, os="Ubuntu", os_version="24.04", architecture="x86_64",
        vagrant_path=MANAGED_ENVIRONMENT_PATH, description="Single Vagrant-managed VMware test environment")
    db.add(environment)
    db.commit()
    db.refresh(environment)
    return environment


def initialize_runtime():
    for name in ("artifacts", "runtime", "logs", "config", "environments"):
        (settings.DATA_DIR / name).mkdir(parents=True, exist_ok=True)
    if IS_FROZEN:
        source = BASE_DIR / "environments" / "ubuntu24" / "Vagrantfile"
        destination = MANAGED_ROOT / "environments" / "ubuntu24" / "Vagrantfile"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    from app.migrate import migrate
    migrate(settings.DATABASE_URL)
    from app.database import SessionLocal
    with SessionLocal() as db:
        register_managed_environment(db)


def setup_complete():
    return (settings.DATA_DIR / "config" / "setup-complete").is_file()


def mark_setup_complete():
    marker = settings.DATA_DIR / "config" / "setup-complete"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("ready\n", encoding="utf-8")
