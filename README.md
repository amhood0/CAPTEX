# CAPTEX

CAPTEX is a local FastAPI web application for managing capabilities, test plans,
and test results. It supports manual result recording and automated execution in
a Vagrant-managed Ubuntu VM using VMware and Ansible.

# Releases

You can find official released versions of CAPTEX here: https://github.com/amhood0/CAPTEX/releases

## Code organization

Requests enter through `app/main.py` and the routes in `app/routers/`. Routes
validate input with `app/schemas.py`, use services in `app/services/` to perform
work, and store records through the SQLAlchemy models in `app/models.py`.
Jinja templates render the pages; JavaScript calls the API and displays operation
progress. Database schema changes live in `alembic/versions/`.

```text
app/
  routers/             API endpoints, page routes, and form handlers
  services/            Test execution, VM control, artifacts, and reporting
  templates/           Jinja HTML pages, grouped by feature
  static/
    css/               Application styles
    js/                Page actions, setup, artifact selection, and progress
    vendor/bootstrap/  Bundled Bootstrap CSS and JavaScript
alembic/               Database migrations and migration configuration code
automation/
  playbooks/           Ansible connectivity and capability-execution playbooks
  files/               Guest test runner and connectivity sample file
environments/ubuntu24/ Managed VM definition (Vagrantfile)
capability_artifacts/  Bundled demo programs and their input files
scripts/               Browser smoke test and live VM/Ansible verification
tests/                 Automated API, service, migration, and regression tests
packaging/             Windows build, installer, icon, and smoke checks
```

## Key files

| File | Purpose |
| --- | --- |
| `app/main.py` | Creates the application, registers routes and static assets, and initializes runtime state. |
| `app/config.py` | Loads settings from environment variables or `.env` and selects data paths. |
| `app/database.py`, `app/models.py`, `app/schemas.py` | Database connections, stored records, and API validation schemas. |
| `app/runtime.py`, `app/migrate.py` | Prepare writable directories, apply migrations, and register the managed environment. |
| `app/errors.py` | Shared error responses. |
| `app/services/automated_runs.py` | Orchestrates automated runs, saves results, and manages VM cleanup. |
| `app/services/capability_execution.py` | Transfers artifacts to the guest, invokes Ansible, and collects results. |
| `app/services/vagrant.py`, `app/services/ansible.py` | Wrappers for VM and guest configuration commands. |
| `app/services/vm_operations.py`, `app/services/automation_operations.py` | Background operations, shared VM locking, and saved progress. |
| `app/services/manual_runs.py`, `app/services/artifacts.py` | Manual run lifecycle and artifact storage/validation. |
| `app/services/demos.py`, `history.py`, `statistics.py` | Under `app/services/`: built-in demo records, run history, and dashboard summaries. |
| `automation/files/capability_runner.py` | Executes test commands in the guest and emits structured results. |
| `automation/inventory.ini` | Ansible inventory for guest configuration. |
| `alembic.ini` | Alembic migration settings. |
| `captex_launcher.py` | Starts the packaged local server, opens the browser, and configures logging. |
| `CAPTEX.spec` | PyInstaller definition for bundling the application and resources. |
| `packaging/build.ps1`, `packaging/CAPTEX.iss` | Build the Windows application and Inno Setup installer. |
| `packaging/captex.ico` | Application and installer icon. |
| `pytest.ini`, `conftest.py` | Test discovery settings and shared test fixtures. |

## Assets and local data

`capability_artifacts/` contains file-creation, process-running, message-only,
and text-summary demos. Each has a `run.py`; the text-summary versions also have
an `input.txt`. Version `text-summary-v2-broken` deliberately reports an incorrect
word count to demonstrate a regression.

UI assets are in `app/static/`, including locally bundled Bootstrap files.
Runtime data is separate from these assets: source runs default to `app.db` and
`.data/`; packaged runs use `%LOCALAPPDATA%\CAPTEX` for the database, artifacts,
logs, and VM state. `CAPTEX_DATA_DIR` and `DATABASE_URL` override these locations.
`.gitignore` excludes local databases, settings, caches, and build output.

## Dependencies and checks

- `requirements.txt`: application dependencies.
- `requirements-dev.txt`: application dependencies plus test tools.
- `requirements-browser.txt`: development dependencies plus Playwright.
- `requirements-build.txt`: development dependencies plus packaging tools.
- `requirements.lock`: exact dependency versions used as install constraints.

Run the test suite with `python -m pytest -q`. The scripts
`scripts/verify_vm.py`, `scripts/verify_ansible.py`, and
`scripts/verify_automated_run.py` provide opt-in live checks; the automated-run
check requires `--live` and starts or changes the managed VM.

## Build and install (Windows)

Install Python and Inno Setup 6, then run these commands in PowerShell from the
repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\packaging\build.ps1
```

The build runs tests and smoke checks. Run
`dist\installer\CAPTEX-Setup-0.1.0.exe` to install, then launch CAPTEX from the
Start menu. Without Inno Setup, use the portable `dist\CAPTEX\CAPTEX.exe` instead.
Follow the installer prompts to install for your Windows user; no administrator privileges are required.
Automated VM tests also require VMware, Vagrant, and the prerequisites shown in
CAPTEX's setup page.
