"""Manual run lifecycle and result snapshots."""
from fastapi import HTTPException
from app.models import TestResult, utc_now

TERMINAL = {"completed", "failed"}


def ensure_editable(run):
    if run.status in TERMINAL:
        raise HTTPException(409, "Completed runs are read-only; create a new run to retest")


def snapshot_cases(run, cases):
    for case in sorted(cases, key=lambda case: (case.execution_order, case.id)):
        if case.enabled:
            run.test_results.append(TestResult(test_case_id=case.id, status="PENDING",
                                               expected_result=case.expected_result))


def change_status(run, status):
    ensure_editable(run)
    now = utc_now()
    if status == "running":
        if not run.test_results:
            raise HTTPException(400, "Add enabled test cases and create a new run before starting")
        run.started_at = run.started_at or now
    elif status == "completed":
        if not run.test_results or any(r.status == "PENDING" for r in run.test_results):
            raise HTTPException(400, "Record a result for every case before completing the run")
        statuses = {r.status for r in run.test_results}
        run.overall_result = "ERROR" if "ERROR" in statuses or statuses == {"SKIPPED"} else "FAIL" if "FAIL" in statuses else "PASS"
        run.started_at = run.started_at or now
        run.completed_at = now
        run.duration = max(0, int((now - run.started_at).total_seconds()))
    elif status == "failed":
        run.overall_result = "ERROR"
        run.started_at = run.started_at or now
        run.completed_at = now
        run.duration = max(0, int((now - run.started_at).total_seconds()))
    elif status != "queued" or run.status != "queued":
        raise HTTPException(400, "Unsupported manual run transition")
    run.status = status
