"""
API integration tests
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import Capability, CapabilityVersion, Environment, TestPlan as ModelTestPlan, TestCase as ModelTestCase



class TestCapabilityAPI:
    """Test Capability API endpoints"""
    
    def test_create_capability(self, client):
        """Test creating a capability via API"""
        data = {
            "name": "Test Capability",
            "category": "Testing",
            "description": "A test capability",
            "active": True
        }
        response = client.post("/api/capabilities", json=data)
        assert response.status_code == 200
        assert response.json()["name"] == "Test Capability"
    
    def test_list_capabilities(self, client):
        """Test listing capabilities"""
        # Create a capability first
        data = {
            "name": "Test Cap",
            "category": "Test",
            "active": True
        }
        client.post("/api/capabilities", json=data)
        
        response = client.get("/api/capabilities")
        assert response.status_code == 200
        capabilities = response.json()
        assert len(capabilities) == 1
        assert capabilities[0]["name"] == "Test Cap"
    
    def test_get_capability(self, client):
        """Test getting a single capability"""
        data = {
            "name": "Test Cap",
            "category": "Test",
            "active": True
        }
        create_response = client.post("/api/capabilities", json=data)
        cap_id = create_response.json()["id"]
        
        response = client.get(f"/api/capabilities/{cap_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Test Cap"
    
    def test_update_capability(self, client):
        """Test updating a capability"""
        data = {
            "name": "Test Cap",
            "category": "Test",
            "active": True
        }
        create_response = client.post("/api/capabilities", json=data)
        cap_id = create_response.json()["id"]
        
        update_data = {
            "name": "Updated Cap",
            "category": "Updated"
        }
        response = client.put(f"/api/capabilities/{cap_id}", json=update_data)
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Cap"
    
    def test_delete_capability(self, client):
        """Test deleting a capability"""
        data = {
            "name": "Test Cap",
            "category": "Test",
            "active": True
        }
        create_response = client.post("/api/capabilities", json=data)
        cap_id = create_response.json()["id"]
        
        response = client.delete(f"/api/capabilities/{cap_id}")
        assert response.status_code == 200
        
        # Verify it's deleted
        get_response = client.get(f"/api/capabilities/{cap_id}")
        assert get_response.status_code == 404


class TestCapabilityVersionAPI:
    """Test CapabilityVersion API endpoints"""
    
    def test_create_version(self, client):
        """Test creating a version"""
        # Create capability first
        cap_data = {
            "name": "Test Cap",
            "category": "Test",
            "active": True
        }
        cap_response = client.post("/api/capabilities", json=cap_data)
        cap_id = cap_response.json()["id"]
        
        # Create version
        version_data = {
            "capability_id": cap_id,
            "version": "1.0.0",
            "description": "First version",
            "entry_point": "main.py"
        }
        response = client.post(f"/api/capabilities/{cap_id}/versions", json=version_data)
        assert response.status_code == 200
        assert response.json()["version"] == "1.0.0"
    
    def test_list_versions(self, client):
        """Test listing versions"""
        cap_data = {
            "name": "Test Cap",
            "category": "Test",
            "active": True
        }
        cap_response = client.post("/api/capabilities", json=cap_data)
        cap_id = cap_response.json()["id"]
        
        version_data = {
            "capability_id": cap_id,
            "version": "1.0.0"
        }
        client.post(f"/api/capabilities/{cap_id}/versions", json=version_data)
        
        response = client.get(f"/api/capabilities/{cap_id}/versions")
        assert response.status_code == 200
        assert len(response.json()) == 1
    
    def test_get_version(self, client):
        """Test getting a version"""
        cap_data = {
            "name": "Test Cap",
            "category": "Test"
        }
        cap_response = client.post("/api/capabilities", json=cap_data)
        cap_id = cap_response.json()["id"]
        
        version_data = {
            "capability_id": cap_id,
            "version": "1.0.0"
        }
        ver_response = client.post(f"/api/capabilities/{cap_id}/versions", json=version_data)
        ver_id = ver_response.json()["id"]
        
        response = client.get(f"/api/capabilities/{cap_id}/versions/{ver_id}")
        assert response.status_code == 200
        assert response.json()["version"] == "1.0.0"
    
    def test_delete_version(self, client):
        """Test deleting a version"""
        cap_data = {
            "name": "Test Cap",
            "category": "Test"
        }
        cap_response = client.post("/api/capabilities", json=cap_data)
        cap_id = cap_response.json()["id"]
        
        version_data = {
            "capability_id": cap_id,
            "version": "1.0.0"
        }
        ver_response = client.post(f"/api/capabilities/{cap_id}/versions", json=version_data)
        ver_id = ver_response.json()["id"]
        
        response = client.delete(f"/api/capabilities/{cap_id}/versions/{ver_id}")
        assert response.status_code == 200
        
        # Verify it's deleted
        get_response = client.get(f"/api/capabilities/{cap_id}/versions/{ver_id}")
        assert get_response.status_code == 404


class TestEnvironmentAPI:
    """Test Environment API endpoints"""
    
    def test_create_environment(self, client):
        """Test creating an environment"""
        data = {
            "name": "Ubuntu Test",
            "os": "Ubuntu",
            "os_version": "24.04",
            "architecture": "x86_64"
        }
        response = client.post("/api/environments", json=data)
        assert response.status_code == 200
        assert response.json()["name"] == "Ubuntu Test"
    
    def test_list_environments(self, client):
        """Test listing environments"""
        data = {
            "name": "Ubuntu Test",
            "os": "Ubuntu"
        }
        client.post("/api/environments", json=data)
        
        response = client.get("/api/environments")
        assert response.status_code == 200
        assert len(response.json()) == 1
    
    def test_delete_environment(self, client):
        """Test deleting an environment"""
        data = {
            "name": "Ubuntu Test",
            "os": "Ubuntu"
        }
        create_response = client.post("/api/environments", json=data)
        env_id = create_response.json()["id"]
        
        response = client.delete(f"/api/environments/{env_id}")
        assert response.status_code == 200


class TestTestPlanAPI:
    """Test ModelTestPlan API endpoints"""
    
    def test_create_test_plan(self, client):
        """Test creating a test plan"""
        # Create capability first
        cap_data = {
            "name": "Test Cap",
            "category": "Test"
        }
        cap_response = client.post("/api/capabilities", json=cap_data)
        cap_id = cap_response.json()["id"]
        
        # Create test plan
        plan_data = {
            "capability_id": cap_id,
            "name": "Basic Tests",
            "description": "Basic test plan",
            "active": True
        }
        response = client.post("/api/test-plans", json=plan_data)
        assert response.status_code == 200
        assert response.json()["name"] == "Basic Tests"
    
    def test_list_test_plans(self, client):
        """Test listing test plans"""
        cap_data = {
            "name": "Test Cap",
            "category": "Test"
        }
        cap_response = client.post("/api/capabilities", json=cap_data)
        cap_id = cap_response.json()["id"]
        
        plan_data = {
            "capability_id": cap_id,
            "name": "Plan"
        }
        client.post("/api/test-plans", json=plan_data)
        
        response = client.get("/api/test-plans")
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestTestCaseAPI:
    """Test ModelTestCase API endpoints"""
    
    def test_create_test_case(self, client):
        """Test creating a test case"""
        # Create capability and plan first
        cap_data = {
            "name": "Test Cap",
            "category": "Test"
        }
        cap_response = client.post("/api/capabilities", json=cap_data)
        cap_id = cap_response.json()["id"]
        
        plan_data = {
            "capability_id": cap_id,
            "name": "Plan"
        }
        plan_response = client.post("/api/test-plans", json=plan_data)
        plan_id = plan_response.json()["id"]
        
        # Create test case
        case_data = {
            "test_plan_id": plan_id,
            "name": "Test 1",
            "test_type": "exit_code",
            "expected_result": "0"
        }
        response = client.post(f"/api/test-plans/{plan_id}/test-cases", json=case_data)
        assert response.status_code == 200
        assert response.json()["name"] == "Test 1"


class TestTestRunAPI:
    """Test ModelTestRun API endpoints"""
    
    def setup_test_data(self, client):
        """Setup test data for runs"""
        # Create capability
        cap_data = {"name": "Test Cap", "category": "Test"}
        cap_response = client.post("/api/capabilities", json=cap_data)
        cap_id = cap_response.json()["id"]
        
        # Create version
        version_data = {
            "capability_id": cap_id,
            "version": "1.0.0"
        }
        ver_response = client.post(f"/api/capabilities/{cap_id}/versions", json=version_data)
        ver_id = ver_response.json()["id"]
        
        # Create plan
        plan_data = {
            "capability_id": cap_id,
            "name": "Plan"
        }
        plan_response = client.post("/api/test-plans", json=plan_data)
        plan_id = plan_response.json()["id"]
        
        client.post(f"/api/test-plans/{plan_id}/test-cases", json={
            "test_plan_id": plan_id, "name": "Exit check", "test_type": "exit_code"
        })

        # Create environment
        env_data = {
            "name": "Ubuntu",
            "os": "Ubuntu"
        }
        env_response = client.post("/api/environments", json=env_data)
        env_id = env_response.json()["id"]
        
        return cap_id, ver_id, plan_id, env_id
    
    def test_create_test_run(self, client):
        """Test creating a test run"""
        cap_id, ver_id, plan_id, env_id = self.setup_test_data(client)
        
        run_data = {
            "capability_version_id": ver_id,
            "test_plan_id": plan_id,
            "environment_id": env_id,
            "initiated_by": "test_user"
        }
        response = client.post("/api/test-runs", json=run_data)
        assert response.status_code == 200
        assert response.json()["status"] == "queued"
    
    def test_list_test_runs(self, client):
        """Test listing test runs"""
        cap_id, ver_id, plan_id, env_id = self.setup_test_data(client)
        
        run_data = {
            "capability_version_id": ver_id,
            "test_plan_id": plan_id,
            "environment_id": env_id
        }
        client.post("/api/test-runs", json=run_data)
        
        response = client.get("/api/test-runs")
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestHealth:
    """Test health endpoint"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
