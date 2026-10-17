"""Bundled examples installed as ordinary capabilities and test plans."""
from app.models import Capability, CapabilityVersion, TestPlan, TestCase

DEMOS = (
    ("Text Summary", "Compare a working version with a deliberate word-count regression.",
     (("1.0", "text-summary-v1"), ("2.0-broken", "text-summary-v2-broken")),
     (("Successful execution", "exit_code", "0"), ("Correct word count", "stdout_contains", "Words: 12"),
      ("Summary file created", "file_exists", "summary.txt"))),
    ("File Creation", "Create a proof file and collect the confirmation message.",
     (("1.0", "file-creation"),),
     (("Successful execution", "exit_code", "0"), ("Confirmation", "stdout_contains", "CAPTEX_PHASE6_DEMO_OK"),
      ("Proof file created", "file_exists", "proof.txt"))),
    ("Message-only Simulation", "Harmless malware-themed message; PASS verifies expected output, not malware detection.",
     (("1.0", "sample-malware"),),
     (("Successful execution", "exit_code", "0"), ("Expected message", "stdout_contains", "youve been hacked"))),
    ("Process Running", "Start a harmless child process, verify it stays running, and clean it up.",
     (("1.0", "process-running"),),
     (("Process verified and stopped", "exit_code", "0"),)),
)


def seed_demos(db):
    """Called once by migration; never replace an existing capability."""
    for name, description, versions, cases in DEMOS:
        if db.query(Capability).filter_by(name=name).first() is not None:
            continue
        capability = Capability(name=name, description=description, category="Built-in demo")
        capability.versions = [CapabilityVersion(version=version, artifact_path=f"bundled:{artifact}",
            entry_point="run.py", execution_command="python3 run.py") for version, artifact in versions]
        plan = TestPlan(name=f"{name} checks", description=description)
        plan.test_cases = [TestCase(name=label, test_type=kind, expected_result=expected,
            execution_order=index, timeout=10, enabled=True)
            for index, (label, kind, expected) in enumerate(cases, 1)]
        capability.test_plans.append(plan)
        db.add(capability)
    db.flush()
