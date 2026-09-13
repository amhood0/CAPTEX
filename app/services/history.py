"""Shared filters for browser and API run history."""
from datetime import date, datetime, time
from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import joinedload, Session, Query
from app.models import TestRun, CapabilityVersion, Capability, TestPlan, Environment


RUN_STATUSES = ("queued", "provisioning", "configuring", "running", "collecting_results", "cleaning_up", "completed", "failed")
OUTCOMES = ("PASS", "FAIL", "ERROR", "CANCELLED")


def history_query(
    db: Session, q: str = "", status: str = "", overall_result: str = "",
    capability_id: str = "", environment_id: str = "", date_from: str = "", date_to: str = "",
) -> Query:
    """Filter creation dates inclusively in UTC and escape literal search text."""
    if len(q) > 200:
        raise HTTPException(422, "Search must be at most 200 characters")
    if status and status not in RUN_STATUSES:
        raise HTTPException(422, "Unknown run status")
    if overall_result and overall_result not in OUTCOMES:
        raise HTTPException(422, "Unknown run outcome")
    query = db.query(TestRun)
    for value, column in ((capability_id, CapabilityVersion.capability_id), (environment_id, TestRun.environment_id)):
        if value:
            try:
                identifier = int(value)
                if identifier < 1:
                    raise ValueError()
            except (ValueError, TypeError):
                raise HTTPException(422, "Filter IDs must be positive integers")
            if column is CapabilityVersion.capability_id:
                query = query.filter(TestRun.capability_version.has(capability_id=identifier))
            else:
                query = query.filter(column == identifier)
    try:
        start = date.fromisoformat(date_from) if date_from else None
        end = date.fromisoformat(date_to) if date_to else None
    except ValueError:
        raise HTTPException(422, "Dates must use YYYY-MM-DD")
    if start and end and start > end:
        raise HTTPException(422, "From date must be on or before To date")
    if start:
        query = query.filter(TestRun.created_at >= datetime.combine(start, time.min))
    if end:
        query = query.filter(TestRun.created_at <= datetime.combine(end, time.max))
    if q:
        pattern = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        query = query.join(CapabilityVersion).join(Capability).join(TestPlan, TestRun.test_plan_id == TestPlan.id).join(Environment)
        query = query.filter(or_(*(column.ilike(pattern, escape="\\") for column in
            (Capability.name, CapabilityVersion.version, TestPlan.name, Environment.name))))
    if status:
        query = query.filter(TestRun.status == status)
    if overall_result:
        query = query.filter(TestRun.overall_result == overall_result)
    return query.order_by(TestRun.created_at.desc(), TestRun.id.desc())


def load_run_details(query: Query) -> Query:
    """Load table relationships without a query for every displayed row."""
    return query.options(joinedload(TestRun.capability_version).joinedload(CapabilityVersion.capability),
                         joinedload(TestRun.test_plan), joinedload(TestRun.environment))
