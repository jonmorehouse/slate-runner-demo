"""Data models for the control plane."""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
import json


class JobStatus(Enum):
    """Job execution status."""
    QUEUED = "queued"              # Job created, waiting to be picked up
    IN_PROGRESS = "in-progress"    # Job claimed and currently running
    SUCCESSFUL = "successful"      # Job completed successfully
    FAILED = "failed"              # Job failed


class JobOperation(Enum):
    """Terraform operation type."""
    PLAN = "plan"
    APPLY = "apply"
    REFRESH = "refresh"
    STATE_SYNC = "state_sync"


class AgentStatus(Enum):
    """Agent connection status."""
    ONLINE = "online"
    OFFLINE = "offline"


@dataclass
class Agent:
    """Represents a runner agent."""
    agent_id: str
    name: str
    status: str = AgentStatus.ONLINE.value
    last_heartbeat: Optional[str] = None
    locked: bool = False
    paused: bool = False
    read_only: bool = False
    adopted: bool = False
    adopted_at: Optional[str] = None
    adopted_by: Optional[str] = None
    connected_at: Optional[str] = None
    disconnected_at: Optional[str] = None
    connection_count: int = 0
    runner_state: Optional[Dict[str, Any]] = None
    terraform_resources: Optional[List[Dict[str, Any]]] = None
    last_state_sync: Optional[str] = None
    last_job_completed: Optional[str] = None
    requires_reconciliation: bool = False
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Agent':
        """Create from dictionary."""
        return cls(**data)
    
    def is_online(self, timeout_seconds: int = 15) -> bool:
        """Check if agent is online based on heartbeat."""
        if not self.last_heartbeat:
            return False
        
        last_beat = datetime.fromisoformat(self.last_heartbeat)
        now = datetime.now(timezone.utc)
        elapsed = (now - last_beat).total_seconds()
        
        return elapsed < timeout_seconds


@dataclass
class Job:
    """Represents a Terraform job."""
    job_id: str
    agent_id: str
    repo_url: str
    operation: str
    status: str = JobStatus.QUEUED.value
    env_vars: Optional[Dict[str, str]] = None
    tfvars: Optional[str] = None
    tf_version: Optional[str] = None
    working_dir: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None
    state_path: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Job':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class HealthCheck:
    """Represents an agent health check."""
    agent_id: str
    timestamp: str
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    disk_percent: Optional[float] = None
    capabilities: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HealthCheck':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class Command:
    """Represents a command sent to an agent."""
    command_id: str
    agent_id: str
    command_type: str  # lock, unlock, pause, unpause, set_read_only
    params: Optional[Dict[str, Any]] = None
    executed: bool = False
    created_at: Optional[str] = None
    executed_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Command':
        """Create from dictionary."""
        return cls(**data)