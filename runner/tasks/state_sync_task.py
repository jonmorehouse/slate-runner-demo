"""State sync task implementation."""
import os
import sys
import json
import requests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from task import Task, TaskContext, TaskResult, TaskStatus
from storage import RunnerS3Client


class StateSyncTask(Task):
    """Sync runner state to control plane."""
    
    def get_type(self) -> str:
        return "state_sync"
    
    def validate(self, context: TaskContext) -> bool:
        """Validate state sync context."""
        return True  # No special validation needed
    
    def execute(self, context: TaskContext) -> TaskResult:
        """Execute state sync - upload runner state and latest terraform states to control plane."""
        try:
            # Get runner state from state manager
            # Note: state manager is passed via context metadata
            state_manager = context.metadata.get('state_manager')
            
            if not state_manager:
                return TaskResult(
                    status=TaskStatus.FAILED,
                    output="",
                    error="State manager not available"
                )
            
            # Get current state
            runner_state = state_manager.get_state()
            
            # Collect all Terraform state files from S3 FOR THIS RUNNER ONLY
            s3_client = RunnerS3Client()
            terraform_states = []
            
            try:
                # List state files ONLY for this runner using runner-isolated prefix
                runner_states_prefix = f'states/{context.runner_id}/'
                state_files = s3_client.list_objects(runner_states_prefix)
                
                for state_key in state_files:
                    if state_key.endswith('terraform.tfstate'):
                        try:
                            # Download state file
                            state_data = s3_client.get_object(state_key)
                            state_json = json.loads(state_data.decode('utf-8'))
                            
                            # Extract job_id from path (states/{runner_id}/{job_id}/terraform.tfstate)
                            path_parts = state_key.split('/')
                            job_id = path_parts[2] if len(path_parts) > 2 else 'unknown'
                            
                            terraform_states.append({
                                'job_id': job_id,
                                'state': state_json
                            })
                        except Exception as e:
                            print(f"[StateSyncTask] Warning: Failed to parse state {state_key}: {e}")
                            continue
                            
            except Exception as e:
                print(f"[StateSyncTask] Warning: Failed to collect terraform states: {e}")
            
            # Upload to control plane
            control_plane_url = context.metadata.get('control_plane_url') or os.getenv('CONTROL_PLANE_URL', 'http://localhost:5005')
            
            response = requests.post(
                f"{control_plane_url}/api/agents/{context.runner_id}/state",
                json={
                    'state': runner_state,
                    'terraform_states': terraform_states
                },
                timeout=30
            )
            
            if response.status_code == 200:
                output = f"State synced successfully\n"
                output += f"Jobs completed: {runner_state.get('jobs_completed', 0)}\n"
                output += f"Jobs failed: {runner_state.get('jobs_failed', 0)}\n"
                output += f"Terraform states: {len(terraform_states)}\n"
                output += f"Last sync: {runner_state.get('last_sync', 'N/A')}\n"
                
                return TaskResult(
                    status=TaskStatus.SUCCESS,
                    output=output,
                    error=None,
                    metadata={'state': runner_state, 'terraform_states_count': len(terraform_states)}
                )
            else:
                return TaskResult(
                    status=TaskStatus.FAILED,
                    output="",
                    error=f"Failed to upload state: {response.status_code}"
                )
                
        except Exception as e:
            import traceback
            return TaskResult(
                status=TaskStatus.FAILED,
                output="",
                error=f"Error syncing state: {str(e)}\n{traceback.format_exc()}"
            )
    
    def cleanup(self, context: TaskContext):
        """No cleanup needed for state sync."""
        pass
    
    def get_timeout(self) -> int:
        """State sync should be fast."""
        return 30  # 30 seconds