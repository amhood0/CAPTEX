"""
Pages router for serving web pages
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pathlib import Path
from sqlalchemy.orm import Session
from fastapi import Depends
from app.database import get_db
from app.models import Capability, CapabilityVersion, Environment, TestPlan, TestRun, TestCase, TestResult
import jinja2
from app.services.history import history_query

# Setup templates
templates_dir = Path(__file__).parent.parent / "templates"
# Escape stored values in HTML templates.
env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(templates_dir)),
    autoescape=jinja2.select_autoescape(["html", "xml"])
)

router = APIRouter()


def render_template(template_name: str, context: dict, request: Request = None) -> str:
    """Render a template with context"""
    # Add url_for function to context for use in templates
    if "url_for" not in context and request:
        context["url_for"] = request.url_for
    template = env.get_template(template_name)
    return template.render(**context)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    """Dashboard page"""
    # Get statistics
    total_capabilities = db.query(Capability).count()
    total_environments = db.query(Environment).count()
    total_test_plans = db.query(TestPlan).count()
    total_test_runs = db.query(TestRun).count()
    
    # Get recent test runs
    recent_runs = db.query(TestRun).order_by(TestRun.created_at.desc()).limit(5).all()
    
    # Calculate pass/fail stats
    pass_count = db.query(TestRun).filter(TestRun.overall_result == "PASS").count()
    fail_count = db.query(TestRun).filter(TestRun.overall_result == "FAIL").count()
    
    pass_rate = 0
    if total_test_runs > 0:
        pass_rate = (pass_count / total_test_runs) * 100
    
    html = render_template("dashboard.html", {
        "request": request,
        "total_capabilities": total_capabilities,
        "total_environments": total_environments,
        "total_test_plans": total_test_plans,
        "total_test_runs": total_test_runs,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pass_rate": round(pass_rate, 1),
        "recent_runs": recent_runs,
    }, request=request)
    return HTMLResponse(html)


@router.get("/capabilities", response_class=HTMLResponse)
def list_capabilities(request: Request, db: Session = Depends(get_db)):
    """List all capabilities"""
    capabilities = db.query(Capability).all()
    
    html = render_template("capabilities/list.html", {
        "request": request,
        "capabilities": capabilities,
    }, request=request)
    return HTMLResponse(html)


@router.get("/capabilities/{capability_id}", response_class=HTMLResponse)
def capability_detail(request: Request, capability_id: int, db: Session = Depends(get_db)):
    """Capability detail page"""
    capability = db.query(Capability).filter(Capability.id == capability_id).first()
    if not capability:
        html = render_template("404.html", {"request": request}, request=request)
        return HTMLResponse(html, status_code=404)
    
    versions = db.query(CapabilityVersion).filter(
        CapabilityVersion.capability_id == capability_id
    ).all()
    
    test_plans = db.query(TestPlan).filter(
        TestPlan.capability_id == capability_id
    ).all()
    
    recent_runs = db.query(TestRun).join(
        CapabilityVersion
    ).filter(
        CapabilityVersion.capability_id == capability_id
    ).order_by(TestRun.created_at.desc()).limit(10).all()
    
    html = render_template("capabilities/detail.html", {
        "request": request,
        "capability": capability,
        "versions": versions,
        "test_plans": test_plans,
        "recent_runs": recent_runs,
    }, request=request)
    return HTMLResponse(html)


@router.get("/environments", response_class=HTMLResponse)
def list_environments(request: Request, db: Session = Depends(get_db)):
    """List all environments"""
    environments = db.query(Environment).all()
    
    html = render_template("environments/list.html", {
        "request": request,
        "environments": environments,
    }, request=request)
    return HTMLResponse(html)


@router.get("/test-plans", response_class=HTMLResponse)
def list_test_plans(request: Request, db: Session = Depends(get_db)):
    """List all test plans"""
    test_plans = db.query(TestPlan).all()
    
    html = render_template("test_plans/list.html", {
        "request": request,
        "test_plans": test_plans,
    }, request=request)
    return HTMLResponse(html)


@router.get("/test-runs", response_class=HTMLResponse)
def list_test_runs(request: Request, q: str = "", status: str = "", overall_result: str = "", db: Session = Depends(get_db)):
    """List all test runs"""
    test_runs = history_query(db, q, status, overall_result).all()
    
    html = render_template("test_runs/list.html", {
        "request": request,
        "test_runs": test_runs, "q": q, "status": status, "overall_result": overall_result,
    }, request=request)
    return HTMLResponse(html)


@router.get("/test-runs/{run_id}", response_class=HTMLResponse)
def test_run_detail(request: Request, run_id: int, db: Session = Depends(get_db)):
    """Test run detail page"""
    test_run = db.query(TestRun).filter(TestRun.id == run_id).first()
    if not test_run:
        html = render_template("404.html", {"request": request}, request=request)
        return HTMLResponse(html, status_code=404)
    
    results = db.query(TestResult).filter(TestResult.test_run_id == run_id).all()
    
    html = render_template("test_runs/detail.html", {
        "request": request,
        "test_run": test_run,
        "results": results,
    }, request=request)
    return HTMLResponse(html)


@router.get("/test-plans/{plan_id}", response_class=HTMLResponse)
def test_plan_detail(request: Request, plan_id: int, db: Session = Depends(get_db)):
    plan = db.get(TestPlan, plan_id)
    if plan is None:
        return HTMLResponse(render_template("404.html", {}, request=request), status_code=404)
    return HTMLResponse(render_template("test_plans/detail.html", {"plan": plan}, request=request))


@router.get("/capabilities/{capability_id}/edit", response_class=HTMLResponse)
def edit_capability(request: Request, capability_id: int, db: Session = Depends(get_db)):
    capability = db.get(Capability, capability_id)
    if capability is None:
        return HTMLResponse(render_template("404.html", {}, request=request), status_code=404)
    fields = [("name", "Name", "text", True), ("category", "Category", "text", True),
              ("description", "Description", "textarea", False), ("active", "Active", "checkbox", False)]
    return HTMLResponse(render_template("edit.html", {
        "title": "Edit capability", "record": capability, "fields": fields,
        "endpoint": f"/api/capabilities/{capability_id}", "back": f"/capabilities/{capability_id}",
    }, request=request))


@router.get("/capabilities/{capability_id}/versions/{version_id}/edit", response_class=HTMLResponse)
def edit_version(request: Request, capability_id: int, version_id: int, db: Session = Depends(get_db)):
    version = db.get(CapabilityVersion, version_id)
    if version is None or version.capability_id != capability_id:
        return HTMLResponse(render_template("404.html", {}, request=request), status_code=404)
    fields = [("version", "Version", "text", True), ("description", "Description", "textarea", False)]
    fields += [(name, name.replace("_", " ").title(), "text", False) for name in
               ("artifact_path", "repository_url", "commit_hash", "entry_point", "execution_command")]
    return HTMLResponse(render_template("edit.html", {
        "title": "Edit version", "record": version, "fields": fields,
        "endpoint": f"/api/capabilities/{capability_id}/versions/{version_id}",
        "back": f"/capabilities/{capability_id}",
    }, request=request))
