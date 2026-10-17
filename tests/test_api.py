"""
API integration tests
"""


class TestCapabilityAPI:
    """Test Capability API endpoints"""
    
    
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


class TestHealth:
    """Test health endpoint"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
