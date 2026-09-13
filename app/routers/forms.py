"""Browser forms for the testing domain; writes use the existing JSON APIs."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Capability, Environment, TestPlan, TestCase, TestResult
from app.routers.pages import render_template

router = APIRouter()
ENV_FIELDS = [(name, label, kind, required) for name, label, kind, required in [
    ("name", "Name", "text", True), ("os", "Operating system", "text", True),
    ("os_version", "OS version", "text", False), ("architecture", "Architecture", "text", True),
    ("description", "Description", "textarea", False), ("vagrant_path", "Vagrant path", "text", False),
    ("ansible_inventory", "Ansible inventory", "text", False)]]
PLAN_FIELDS = [("name", "Name", "text", True), ("description", "Description", "textarea", False), ("active", "Active", "checkbox", False)]
CASE_FIELDS = [("name", "Name", "text", True), ("description", "Description", "textarea", False),
    ("test_type", "Test type", "select", True), ("expected_result", "Expected result", "textarea", False),
    ("execution_order", "Execution order", "number", True), ("timeout", "Timeout (seconds)", "number", True),
    ("enabled", "Enabled", "checkbox", False)]
CASE_CHOICES = {"test_type": [(t, t.replace("_", " ").title()) for t in ("exit_code", "stdout_contains", "file_exists")]}


def get_record(db, model, record_id):
    record = db.get(model, record_id)
    if record is None:
        raise HTTPException(404, "Record not found")
    return record


def form(request, title, record, fields, endpoint, back, method="PUT", choices=None):
    return HTMLResponse(render_template("edit.html", dict(title=title, record=record, fields=fields,
        endpoint=endpoint, back=back, method=method, choices=choices or {}), request=request))


@router.get("/environments/new")
def new_environment(request: Request):
    return form(request, "New environment", {"architecture": "x86_64"}, ENV_FIELDS,
                "/api/environments", "/environments", "POST")


@router.get("/environments/{environment_id}/edit")
def edit_environment(request: Request, environment_id: int, db: Session = Depends(get_db)):
    return form(request, "Edit environment", get_record(db, Environment, environment_id), ENV_FIELDS + [("status", "Status", "select", True)],
                f"/api/environments/{environment_id}", "/environments", choices={"status": [(s, s) for s in ("available", "in_use", "error")]})


@router.get("/test-plans/new")
def new_plan(request: Request, db: Session = Depends(get_db)):
    choices = {"capability_id": [(c.id, c.name) for c in db.query(Capability).order_by(Capability.name)]}
    return form(request, "New test plan", {"active": True}, [("capability_id", "Capability", "select", True)] + PLAN_FIELDS,
                "/api/test-plans", "/test-plans", "POST", choices)


@router.get("/test-plans/{plan_id}/edit")
def edit_plan(request: Request, plan_id: int, db: Session = Depends(get_db)):
    return form(request, "Edit test plan", get_record(db, TestPlan, plan_id), PLAN_FIELDS,
                f"/api/test-plans/{plan_id}", f"/test-plans/{plan_id}")


@router.get("/test-plans/{plan_id}/cases/new")
def new_case(request: Request, plan_id: int, db: Session = Depends(get_db)):
    get_record(db, TestPlan, plan_id)
    return form(request, "New test case", {"test_plan_id": plan_id, "enabled": True, "timeout": 30, "execution_order": 0},
                [("test_plan_id", "", "hidden", True)] + CASE_FIELDS, f"/api/test-plans/{plan_id}/test-cases",
                f"/test-plans/{plan_id}", "POST", CASE_CHOICES)


@router.get("/test-cases/{case_id}/edit")
def edit_case(request: Request, case_id: int, db: Session = Depends(get_db)):
    case = get_record(db, TestCase, case_id)
    return form(request, "Edit test case", case, CASE_FIELDS, f"/api/test-cases/{case_id}",
                f"/test-plans/{case.test_plan_id}", choices=CASE_CHOICES)


@router.get("/test-results/{result_id}/edit")
def edit_result(request: Request, result_id: int, db: Session = Depends(get_db)):
    from app.services.manual_runs import ensure_editable
    result = get_record(db, TestResult, result_id)
    ensure_editable(result.test_run)
    fields = [("status", "Outcome", "select", True)]
    fields += [(name, label, kind, False) for name, label, kind in [
        ("expected_result", "Expected result", "textarea"), ("actual_result", "Actual result", "textarea"),
        ("stdout", "Standard output", "textarea"), ("stderr", "Standard error", "textarea"),
        ("exit_code", "Exit code", "number"), ("duration", "Duration (milliseconds)", "number"), ("notes", "Notes", "textarea")]]
    return form(request, f"Record result: {result.test_case.name}", result, fields,
                f"/api/test-results/{result_id}", f"/test-runs/{result.test_run_id}",
                choices={"status": [(s, s) for s in ("PENDING", "PASS", "FAIL", "ERROR", "SKIPPED")]})


@router.get("/test-runs/new")
def new_run(request: Request, db: Session = Depends(get_db)):
    capabilities = [{"id": c.id, "name": c.name,
        "versions": [{"id": v.id, "name": v.version} for v in c.versions],
        "plans": [{"id": p.id, "name": p.name} for p in c.test_plans if p.active and any(t.enabled for t in p.test_cases)]}
        for c in db.query(Capability).filter(Capability.active.is_(True)).order_by(Capability.name)]
    return HTMLResponse(render_template("test_runs/new.html", {"capabilities": capabilities,
        "environments": db.query(Environment).order_by(Environment.name).all()}, request=request))
