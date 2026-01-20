"""Runner state management using SlateDB."""
import json
from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from slate_storage import SlateDBStorage


class RunnerStateManager:
    """Manages runner state persistence using SlateDB."""
    
    def __init__(self, runner_id: str, slate_storage: 'SlateDBStorage'):
        """Initialize state manager.
        
        Args:
            runner_id: Unique runner identifier
            slate_storage: SlateDBStorage instance for persistence
        """
        self.runner_id = runner_id
        self.slate_storage = slate_storage
        self.state_key = f"runner-state/{runner_id}/state.json"
        
        print(f"[StateManager] Using SlateDB for state persistence, key={self.state_key}")
        self._state = self._load_state()
    
    def _load_state(self) -> Dict[str, Any]:
        """Load state from SlateDB."""
        try:
            state_data = self.slate_storage.get(self.state_key)
            if state_data:
                return json.loads(state_data.decode('utf-8'))
            else:
                # Initialize new state
                return {
                    'runner_id': self.runner_id,
                    'created_at': datetime.utcnow().isoformat(),
                    'last_sync': None,
                    'jobs_completed': 0,
                    'jobs_failed': 0,
                    'config': {},
                    'metadata': {},
                    'checkpoints': []
                }
        except Exception as e:
            print(f"[StateManager] Error loading state: {e}, initializing new state")
            return {
                'runner_id': self.runner_id,
                'created_at': datetime.utcnow().isoformat(),
                'last_sync': None,
                'jobs_completed': 0,
                'jobs_failed': 0,
                'config': {},
                'metadata': {},
                'checkpoints': []
            }
    
    def save(self) -> None:
        """Save current state to SlateDB."""
        self._state['last_sync'] = datetime.utcnow().isoformat()
        
        json_data = json.dumps(self._state, indent=2)
        self.slate_storage.put(self.state_key, json_data.encode('utf-8'))
    
    def get(self, key: str, default=None) -> Any:
        """Get a value from state."""
        return self._state.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in state."""
        self._state[key] = value
    
    def increment(self, key: str, amount: int = 1) -> None:
        """Increment a numeric value."""
        current = self._state.get(key, 0)
        self._state[key] = current + amount
    
    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """Update metadata."""
        if 'metadata' not in self._state:
            self._state['metadata'] = {}
        self._state['metadata'].update(metadata)
    
    def get_state(self) -> Dict[str, Any]:
        """Get entire state."""
        return self._state.copy()
    
    def record_job_completion(self, job_id: str, success: bool = True) -> None:
        """Record a completed job ID.
        
        Args:
            job_id: The job ID to record
            success: Whether the job succeeded or failed
        """
        if 'completed_jobs' not in self._state:
            self._state['completed_jobs'] = []
        
        job_record = {
            'job_id': job_id,
            'completed_at': datetime.utcnow().isoformat(),
            'success': success
        }
        
        self._state['completed_jobs'].append(job_record)
        
        # Update counters
        if success:
            self.increment('jobs_completed')
        else:
            self.increment('jobs_failed')
        
        print(f"[StateManager] Recorded job {job_id} (success={success})")
        
        # Save state to SlateDB
        self.save()
    
    def record_checkpoint(self, checkpoint_id: str, job_id: Optional[str] = None, checkpoint_type: str = "post_job") -> None:
        """Record a checkpoint creation.
        
        Args:
            checkpoint_id: The checkpoint ID
            job_id: Associated job ID (if any)
            checkpoint_type: Type of checkpoint
        """
        if 'checkpoints' not in self._state:
            self._state['checkpoints'] = []
        
        checkpoint_record = {
            'checkpoint_id': checkpoint_id,
            'job_id': job_id,
            'type': checkpoint_type,
            'created_at': datetime.utcnow().isoformat()
        }
        
        self._state['checkpoints'].append(checkpoint_record)
        
        print(f"[StateManager] Recorded checkpoint {checkpoint_id} (type={checkpoint_type})")
        
        # Save state
        self.save()
