"""Consistent dashboard and capability summaries."""
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models import TestRun, CapabilityVersion


def run_statistics(db: Session, capability_id: int | None = None) -> dict:
    query = db.query(TestRun.status, TestRun.overall_result, func.count(TestRun.id))
    if capability_id is not None:
        query = query.join(CapabilityVersion).filter(CapabilityVersion.capability_id == capability_id)
    summary = dict(total=0, queued=0, active=0, completed=0, failed=0, passed=0,
                   not_passed=0, errors=0, cancelled=0)
    for status, result, count in query.group_by(TestRun.status, TestRun.overall_result):
        summary["total"] += count
        if status in ("queued", "completed", "failed"):
            summary[status] += count
        else:
            summary["active"] += count
        if status in ("completed", "failed"):
            key = {"PASS": "passed", "FAIL": "not_passed", "ERROR": "errors", "CANCELLED": "cancelled"}.get(result)
            if key:
                summary[key] += count
    evaluated = summary["passed"] + summary["not_passed"]
    summary["pass_rate"] = round(100 * summary["passed"] / evaluated, 1) if evaluated else None
    return summary
