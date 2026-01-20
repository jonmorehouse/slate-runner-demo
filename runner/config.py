"""Runner configuration and state management."""
import os
from dataclasses import dataclass
from typing import Optional
from name_generator import generate_runner_name, generate_runner_id


@dataclass
class RunnerConfig:
    """Configuration for the runner."""
    runner_id: str
    runner_name: str
    control_plane_url: str
    poll_interval: int
    locked: bool = False
    paused: bool = False
    read_only: bool = False
    adopted: bool = False
    requires_reconciliation: bool = False
    last_job_completed_at: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'RunnerConfig':
        """Create config from environment variables."""
        # Generate ID if not provided
        runner_id = os.getenv('RUNNER_ID', '').strip()
        if not runner_id:
            runner_id = generate_runner_id()
            print(f"[Config] Generated runner ID: {runner_id}")
        
        # Generate name if not provided
        runner_name = os.getenv('RUNNER_NAME', '').strip()
        if not runner_name:
            runner_name = generate_runner_name()
            print(f"[Config] Generated runner name: {runner_name}")
        
        return cls(
            runner_id=runner_id,
            runner_name=runner_name,
            control_plane_url=os.getenv('CONTROL_PLANE_URL', 'http://localhost:5005'),
            poll_interval=int(os.getenv('POLL_INTERVAL', '60'))
        )
    
    def apply_command(self, command_type: str, params: Optional[dict] = None):
        """Apply a command to update runner state."""
        if command_type == 'lock':
            self.locked = True
        elif command_type == 'unlock':
            self.locked = False
        elif command_type == 'pause':
            self.paused = True
        elif command_type == 'unpause':
            self.paused = False
        elif command_type == 'set_read_only':
            if params:
                self.read_only = params.get('value', False)
    
    def update_from_agent_data(self, agent_data: dict) -> None:
        """Update config from agent data from control plane."""
        self.locked = agent_data.get('locked', False)
        self.paused = agent_data.get('paused', False)
        self.read_only = agent_data.get('read_only', False)
        self.adopted = agent_data.get('adopted', False)
    
    def can_execute_jobs(self) -> bool:
        """Check if runner can execute jobs."""
        can_execute, _ = self.can_execute_jobs_with_reason()
        return can_execute
    
    def can_execute_jobs_with_reason(self, operation: Optional[str] = None) -> tuple:
        """Check if runner can execute jobs and return reason if not.
        
        Args:
            operation: Job operation type (e.g., 'state_sync', 'plan', 'apply')
        
        Returns:
            (can_execute: bool, reason: str)
        """
        if not self.adopted:
            return False, "runner not yet adopted by control plane"
        
        if self.locked:
            return False, "runner is locked"
        
        if self.paused:
            return False, "runner is paused"
        
        if self.read_only:
            return False, "runner is in read-only mode"
        
        # State sync jobs can run even when reconciliation is needed
        if self.requires_reconciliation and operation != 'state_sync':
            return False, "state has not been reconciled since last job"
        
        return True, ""