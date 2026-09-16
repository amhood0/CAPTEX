"""
Pydantic schemas for request/response validation
"""
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator



class UpdateModel(BaseModel):
    """Allow omitted fields, but reject null for required database values."""
    @model_validator(mode="before")
    @classmethod
    def validate_required_values(cls, values):
        required = {"name", "category", "os", "architecture", "active", "enabled", "version",
                    "status", "test_type", "execution_order", "timeout"}
        if not isinstance(values, dict):
            raise ValueError("Updates must be JSON objects")
        for key, value in values.items():
            if key in required and value is None:
                raise ValueError(f"{key} cannot be null")
        return values

# ============================================================================
# Capability Schemas
# ============================================================================

class CapabilityBase(BaseModel):
    """Base capability schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=100)
    active: bool = True


class CapabilityCreate(CapabilityBase):
    """Create capability schema"""
    pass


class CapabilityUpdate(UpdateModel):
    """Update capability schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    active: Optional[bool] = None


class CapabilityResponse(CapabilityBase):
    """Capability response schema"""
    id: int
    created_at: datetime
    versions: List['CapabilityVersionResponse'] = []
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# CapabilityVersion Schemas
# ============================================================================

class CapabilityVersionBase(BaseModel):
    """Base capability version schema"""
    version: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    artifact_path: Optional[str] = None
    repository_url: Optional[str] = None
    commit_hash: Optional[str] = None
    entry_point: Optional[str] = None
    execution_command: Optional[str] = None


class CapabilityVersionCreate(CapabilityVersionBase):
    """Create capability version schema"""
    capability_id: int


class CapabilityVersionUpdate(UpdateModel):
    """Update capability version schema"""
    version: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    artifact_path: Optional[str] = None
    repository_url: Optional[str] = None
    commit_hash: Optional[str] = None
    entry_point: Optional[str] = None
    execution_command: Optional[str] = None


class CapabilityVersionResponse(CapabilityVersionBase):
    """Capability version response schema"""
    id: int
    capability_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Environment Schemas
# ============================================================================

class EnvironmentBase(BaseModel):
    """Base environment schema"""
    name: str = Field(..., min_length=1, max_length=255)
    os: str = Field(..., min_length=1, max_length=100)
    os_version: Optional[str] = Field(None, max_length=50)
    architecture: str = "x86_64"
    vagrant_path: Optional[str] = None
    ansible_inventory: Optional[str] = None
    description: Optional[str] = None


class EnvironmentCreate(EnvironmentBase):
    """Create environment schema"""
    pass


class EnvironmentUpdate(UpdateModel):
    """Update environment schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    os: Optional[str] = Field(None, min_length=1, max_length=100)
    os_version: Optional[str] = Field(None, max_length=50)
    architecture: Optional[str] = None
    vagrant_path: Optional[str] = None
    ansible_inventory: Optional[str] = None
    description: Optional[str] = None
    status: Optional[Literal["available", "in_use", "error"]] = None


class EnvironmentResponse(EnvironmentBase):
    """Environment response schema"""
    id: int
    status: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# TestPlan Schemas
# ============================================================================

class TestPlanBase(BaseModel):
    """Base test plan schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    active: bool = True


class TestPlanCreate(TestPlanBase):
    """Create test plan schema"""
    capability_id: int


class TestPlanUpdate(UpdateModel):
    """Update test plan schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    active: Optional[bool] = None


class TestPlanResponse(TestPlanBase):
    """Test plan response schema"""
    id: int
    capability_id: int
    created_at: datetime
    test_cases: List['TestCaseResponse'] = []
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# TestCase Schemas
# ============================================================================

class TestCaseBase(BaseModel):
    """Base test case schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    test_type: Literal["exit_code", "stdout_contains", "file_exists"]
    expected_result: Optional[str] = None
    execution_order: int = 0
    timeout: int = Field(30, gt=0)
    enabled: bool = True


class TestCaseCreate(TestCaseBase):
    """Create test case schema"""
    test_plan_id: int


class TestCaseUpdate(UpdateModel):
    """Update test case schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    test_type: Optional[Literal["exit_code", "stdout_contains", "file_exists"]] = None
    expected_result: Optional[str] = None
    execution_order: Optional[int] = None
    timeout: Optional[int] = Field(None, gt=0)
    enabled: Optional[bool] = None


class TestCaseResponse(TestCaseBase):
    """Test case response schema"""
    id: int
    test_plan_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# TestRun Schemas
# ============================================================================

class TestRunBase(BaseModel):
    """Base test run schema"""
    capability_version_id: int
    test_plan_id: int
    environment_id: int
    initiated_by: str = "system"


class TestRunCreate(TestRunBase):
    """Create test run schema"""
    pass


class TestRunResponse(BaseModel):
    """Test run response schema"""
    id: int
    capability_version_id: int
    test_plan_id: int
    environment_id: int
    status: str
    overall_result: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[int] = Field(None, ge=0)
    initiated_by: str
    error_message: Optional[str] = None
    created_at: datetime
    test_results: List['TestResultResponse'] = []
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# TestResult Schemas
# ============================================================================

class TestResultBase(BaseModel):
    """Base test result schema"""
    status: Literal["PENDING", "PASS", "FAIL", "ERROR", "SKIPPED"]
    expected_result: Optional[str] = None
    actual_result: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    exit_code: Optional[int] = None
    duration: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None


class TestResultCreate(TestResultBase):
    """Create test result schema"""
    test_run_id: int
    test_case_id: int


class TestResultUpdate(UpdateModel):
    """Update test result schema"""
    status: Optional[Literal["PENDING", "PASS", "FAIL", "ERROR", "SKIPPED"]] = None
    expected_result: Optional[str] = None
    actual_result: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    exit_code: Optional[int] = None
    duration: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None


class TestResultResponse(TestResultBase):
    """Test result response schema"""
    id: int
    test_run_id: int
    test_case_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Update forward references
CapabilityResponse.model_rebuild()
TestPlanResponse.model_rebuild()
TestRunResponse.model_rebuild()
