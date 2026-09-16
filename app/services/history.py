"""Shared filters for browser and API run history."""
from sqlalchemy import or_
from app.models import TestRun, CapabilityVersion, Capability, TestPlan, Environment


def history_query(db, q="", status="", overall_result=""):
    query = db.query(TestRun)
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
