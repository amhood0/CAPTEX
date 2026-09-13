"""
SQLAlchemy models for the application
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base
import enum


def utc_now():
    """Store UTC timestamps as naive values for SQLite compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Capability(Base):
    """Capability model"""
    __tablename__ = "capabilities"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    category = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    active = Column(Boolean, default=True)
    
    # Relationships
    versions = relationship("CapabilityVersion", back_populates="capability", cascade="all, delete-orphan")
    test_plans = relationship("TestPlan", back_populates="capability", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Capability {self.name}>"


class CapabilityVersion(Base):
    """Capability Version model"""
    __tablename__ = "capability_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    capability_id = Column(Integer, ForeignKey("capabilities.id"), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    description = Column(Text)
    artifact_path = Column(String(500))
    repository_url = Column(String(500))
    commit_hash = Column(String(100))
    entry_point = Column(String(255))
    execution_command = Column(String(500))
    created_at = Column(DateTime, default=utc_now, nullable=False)
    
    # Relationships
    capability = relationship("Capability", back_populates="versions")
    test_runs = relationship("TestRun", back_populates="capability_version")
    
    def __repr__(self):
        return f"<CapabilityVersion {self.capability_id} v{self.version}>"


class Environment(Base):
    """Test Environment model"""
    __tablename__ = "environments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    os = Column(String(100), nullable=False)
    os_version = Column(String(50))
    architecture = Column(String(50), default="x86_64")
    vagrant_path = Column(String(500))
    ansible_inventory = Column(String(500))
    description = Column(Text)
    status = Column(String(50), default="available")  # available, in_use, error
    created_at = Column(DateTime, default=utc_now, nullable=False)
    
    # Relationships
    test_runs = relationship("TestRun", back_populates="environment")
    
    def __repr__(self):
        return f"<Environment {self.name}>"


class TestPlan(Base):
    """Test Plan model"""
    __tablename__ = "test_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    capability_id = Column(Integer, ForeignKey("capabilities.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    
    # Relationships
    capability = relationship("Capability", back_populates="test_plans")
    test_cases = relationship("TestCase", back_populates="test_plan", cascade="all, delete-orphan")
    test_runs = relationship("TestRun", back_populates="test_plan")
    
    def __repr__(self):
        return f"<TestPlan {self.name}>"


class TestCase(Base):
    """Test Case model"""
    __tablename__ = "test_cases"
    
    id = Column(Integer, primary_key=True, index=True)
    test_plan_id = Column(Integer, ForeignKey("test_plans.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    test_type = Column(String(50), nullable=False)  # exit_code, stdout_contains, file_exists
    expected_result = Column(Text)
    execution_order = Column(Integer, default=0)
    timeout = Column(Integer, default=30)  # seconds
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    
    # Relationships
    test_plan = relationship("TestPlan", back_populates="test_cases")
    test_results = relationship("TestResult", back_populates="test_case", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TestCase {self.name}>"


class TestRunStatus(str, enum.Enum):
    """Test run status enum"""
    QUEUED = "queued"
    PROVISIONING = "provisioning"
    CONFIGURING = "configuring"
    RUNNING = "running"
    COLLECTING_RESULTS = "collecting_results"
    CLEANING_UP = "cleaning_up"
    COMPLETED = "completed"
    FAILED = "failed"


class TestResultStatus(str, enum.Enum):
    """Test result status enum"""
    PENDING = "PENDING"
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


class TestRun(Base):
    """Test Run model"""
    __tablename__ = "test_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    capability_version_id = Column(Integer, ForeignKey("capability_versions.id"), nullable=False, index=True)
    test_plan_id = Column(Integer, ForeignKey("test_plans.id"), nullable=False, index=True)
    environment_id = Column(Integer, ForeignKey("environments.id"), nullable=False, index=True)
    status = Column(String(50), default=TestRunStatus.QUEUED.value)
    overall_result = Column(String(20))  # PASS, FAIL, ERROR, CANCELLED
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration = Column(Integer)  # seconds
    initiated_by = Column(String(255), default="system")
    error_message = Column(Text)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    
    # Relationships
    capability_version = relationship("CapabilityVersion", back_populates="test_runs")
    test_plan = relationship("TestPlan", back_populates="test_runs")
    environment = relationship("Environment", back_populates="test_runs")
    test_results = relationship("TestResult", back_populates="test_run", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TestRun {self.id}>"


class TestResult(Base):
    """Test Result model"""
    __tablename__ = "test_results"
    
    id = Column(Integer, primary_key=True, index=True)
    test_run_id = Column(Integer, ForeignKey("test_runs.id"), nullable=False, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False)  # PASS, FAIL, ERROR, SKIPPED
    expected_result = Column(Text)
    actual_result = Column(Text)
    stdout = Column(Text)
    stderr = Column(Text)
    exit_code = Column(Integer)
    duration = Column(Integer)  # milliseconds
    notes = Column(Text)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    
    # Relationships
    test_run = relationship("TestRun", back_populates="test_results")
    test_case = relationship("TestCase", back_populates="test_results")
    
    def __repr__(self):
        return f"<TestResult {self.id}>"
