"""
Unit tests for models and database operations
"""
import pytest
from datetime import datetime
from app.models import (
    Capability, CapabilityVersion, Environment,
    TestPlan as ModelTestPlan, TestCase as ModelTestCase, TestRun as ModelTestRun, TestResult as ModelTestResult
)



class TestCapabilityModel:
    """Test Capability model"""
    
    def test_create_capability(self, db):
        """Test creating a capability"""
        capability = Capability(
            name="Test Capability",
            description="A test capability",
            category="Testing",
            active=True
        )
        db.add(capability)
        db.commit()
        db.refresh(capability)
        
        assert capability.id is not None
        assert capability.name == "Test Capability"
        assert capability.category == "Testing"
        assert capability.active is True
    
    def test_capability_with_versions(self, db):
        """Test capability with versions"""
        capability = Capability(
            name="Test Capability",
            category="Testing",
            active=True
        )
        db.add(capability)
        db.flush()
        
        version = CapabilityVersion(
            capability_id=capability.id,
            version="1.0.0",
            description="Initial version"
        )
        db.add(version)
        db.commit()
        
        db.refresh(capability)
        assert len(capability.versions) == 1
        assert capability.versions[0].version == "1.0.0"


class TestCapabilityVersionModel:
    """Test CapabilityVersion model"""
    
    def test_create_version(self, db):
        """Test creating a capability version"""
        capability = Capability(name="Test Cap", category="Test")
        db.add(capability)
        db.flush()
        
        version = CapabilityVersion(
            capability_id=capability.id,
            version="1.0.0",
            description="Test version",
            entry_point="main.py",
            execution_command="python main.py"
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        
        assert version.id is not None
        assert version.version == "1.0.0"
        assert version.entry_point == "main.py"


class TestEnvironmentModel:
    """Test Environment model"""
    
    def test_create_environment(self, db):
        """Test creating an environment"""
        env = Environment(
            name="Ubuntu Test",
            os="Ubuntu",
            os_version="24.04",
            architecture="x86_64",
            status="available"
        )
        db.add(env)
        db.commit()
        db.refresh(env)
        
        assert env.id is not None
        assert env.name == "Ubuntu Test"
        assert env.os == "Ubuntu"
        assert env.status == "available"


class TestTestPlanAndCaseModels:
    """Test ModelTestPlan and ModelTestCase models"""
    
    def test_create_test_plan(self, db):
        """Test creating a test plan"""
        capability = Capability(name="Test Cap", category="Test")
        db.add(capability)
        db.flush()
        
        plan = ModelTestPlan(
            capability_id=capability.id,
            name="Basic Tests",
            description="Basic test plan",
            active=True
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        
        assert plan.id is not None
        assert plan.name == "Basic Tests"
    
    def test_create_test_case(self, db):
        """Test creating a test case"""
        capability = Capability(name="Test Cap", category="Test")
        db.add(capability)
        db.flush()
        
        plan = ModelTestPlan(capability_id=capability.id, name="Plan")
        db.add(plan)
        db.flush()
        
        case = ModelTestCase(
            test_plan_id=plan.id,
            name="Test 1",
            test_type="exit_code",
            expected_result="0",
            timeout=30
        )
        db.add(case)
        db.commit()
        db.refresh(case)
        
        assert case.id is not None
        assert case.test_type == "exit_code"
        assert case.timeout == 30
    
    def test_test_plan_with_cases(self, db):
        """Test test plan with cases"""
        capability = Capability(name="Test Cap", category="Test")
        db.add(capability)
        db.flush()
        
        plan = ModelTestPlan(capability_id=capability.id, name="Plan")
        db.add(plan)
        db.flush()
        
        for i in range(3):
            case = ModelTestCase(
                test_plan_id=plan.id,
                name=f"Test {i}",
                test_type="exit_code"
            )
            db.add(case)
        
        db.commit()
        db.refresh(plan)
        
        assert len(plan.test_cases) == 3


class TestTestRunAndResultModels:
    """Test ModelTestRun and ModelTestResult models"""
    
    def test_create_test_run(self, db):
        """Test creating a test run"""
        capability = Capability(name="Test Cap", category="Test")
        db.add(capability)
        db.flush()
        
        version = CapabilityVersion(capability_id=capability.id, version="1.0")
        db.add(version)
        db.flush()
        
        plan = ModelTestPlan(capability_id=capability.id, name="Plan")
        db.add(plan)
        db.flush()
        
        env = Environment(name="Ubuntu", os="Ubuntu")
        db.add(env)
        db.flush()
        
        run = ModelTestRun(
            capability_version_id=version.id,
            test_plan_id=plan.id,
            environment_id=env.id,
            status="queued"
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        
        assert run.id is not None
        assert run.status == "queued"
    
    def test_create_test_result(self, db):
        """Test creating a test result"""
        capability = Capability(name="Test Cap", category="Test")
        db.add(capability)
        db.flush()
        
        version = CapabilityVersion(capability_id=capability.id, version="1.0")
        db.add(version)
        db.flush()
        
        plan = ModelTestPlan(capability_id=capability.id, name="Plan")
        db.add(plan)
        db.flush()
        
        case = ModelTestCase(test_plan_id=plan.id, name="Test 1", test_type="exit_code")
        db.add(case)
        db.flush()
        
        env = Environment(name="Ubuntu", os="Ubuntu")
        db.add(env)
        db.flush()
        
        run = ModelTestRun(
            capability_version_id=version.id,
            test_plan_id=plan.id,
            environment_id=env.id
        )
        db.add(run)
        db.flush()
        
        result = ModelTestResult(
            test_run_id=run.id,
            test_case_id=case.id,
            status="PASS",
            expected_result="0",
            actual_result="0",
            exit_code=0,
            stdout="Success"
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        
        assert result.id is not None
        assert result.status == "PASS"
        assert result.exit_code == 0
