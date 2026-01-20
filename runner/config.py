"""Runner configuration and state management."""
import os
from dataclasses import dataclass
from typing import Optional


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
    
    @classmethod
    def from_env(cls) -> 'RunnerConfig':
        """Create config from environment variables."""
        return cls(
            runner_id=os.getenv('RUNNER_ID', 'runner-001'),
            runner_name=os.getenv('RUNNER_NAME', 'Demo Runner'),
            control_plane_url=os.getenv('CONTROL_PLANE_URL', 'http://localhost:5005'),
            poll_interval=int(os.getenv('POLL_INTERVAL', '5'))
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
        return self.adopted and not (self.locked or self.paused or self.read_only)