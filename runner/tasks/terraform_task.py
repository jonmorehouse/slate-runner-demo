"""Terraform task implementations."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from task import Task, TaskContext, TaskResult, TaskStatus
from terraform import TerraformExecutor


class BaseTerraformTask(Task):
    """Base class for Terraform tasks."""
    
    def __init__(self):
        """Initialize Terraform task."""
        self.terraform = None  # Initialized per execution with version
    
    def _get_executor(self, context: TaskContext) -> TerraformExecutor:
        """Get or create TerraformExecutor with job-specific version."""
        tf_version = context.config.get('tf_version')
        return TerraformExecutor(tf_version=tf_version)
    
    def validate(self, context: TaskContext) -> bool:
        """Validate Terraform task context."""
        config = context.config
        
        # Check required fields
        if not config.get('repo_url'):
            return False
        
        return True
    
    def cleanup(self, context: TaskContext):
        """Cleanup Terraform working directory."""
        if self.terraform:
            self.terraform.cleanup()


class TerraformPlanTask(BaseTerraformTask):
    """Execute terraform plan operation."""
    
    def get_type(self) -> str:
        return "plan"
    
    def execute(self, context: TaskContext) -> TaskResult:
        """Execute terraform plan."""
        config = context.config
        
        try:
            self.terraform = self._get_executor(context)
            success, output, state_path = self.terraform.execute_job(
                repo_url=config['repo_url'],
                operation='plan',
                env_vars=context.env_vars,
                tfvars=config.get('tfvars'),
                working_dir=config.get('working_dir')
            )
            
            artifacts = {}
            if state_path:
                artifacts['state_path'] = state_path
            
            return TaskResult(
                status=TaskStatus.SUCCESS if success else TaskStatus.FAILED,
                output=output,
                error=None if success else output,
                artifacts=artifacts
            )
            
        except Exception as e:
            return TaskResult(
                status=TaskStatus.FAILED,
                output="",
                error=str(e)
            )
    
    def get_timeout(self) -> int:
        """Plan operations typically faster than apply."""
        return 300  # 5 minutes


class TerraformApplyTask(BaseTerraformTask):
    """Execute terraform apply operation."""
    
    def get_type(self) -> str:
        return "apply"
    
    def execute(self, context: TaskContext) -> TaskResult:
        """Execute terraform apply."""
        config = context.config
        
        try:
            self.terraform = self._get_executor(context)
            success, output, state_path = self.terraform.execute_job(
                repo_url=config['repo_url'],
                operation='apply',
                env_vars=context.env_vars,
                tfvars=config.get('tfvars'),
                working_dir=config.get('working_dir')
            )
            
            artifacts = {}
            if state_path:
                artifacts['state_path'] = state_path
            
            return TaskResult(
                status=TaskStatus.SUCCESS if success else TaskStatus.FAILED,
                output=output,
                error=None if success else output,
                artifacts=artifacts,
                metadata={
                    'operation': 'apply',
                    'repo': config['repo_url']
                }
            )
            
        except Exception as e:
            return TaskResult(
                status=TaskStatus.FAILED,
                output="",
                error=str(e)
            )
    
    def can_retry(self, error: Exception) -> bool:
        """Apply operations generally shouldn't be auto-retried."""
        return False
    
    def get_timeout(self) -> int:
        """Apply operations can take longer."""
        return 900  # 15 minutes


class TerraformRefreshTask(BaseTerraformTask):
    """Execute terraform refresh operation."""
    
    def get_type(self) -> str:
        return "refresh"
    
    def execute(self, context: TaskContext) -> TaskResult:
        """Execute terraform refresh."""
        config = context.config
        
        try:
            self.terraform = self._get_executor(context)
            success, output, state_path = self.terraform.execute_job(
                repo_url=config['repo_url'],
                operation='refresh',
                env_vars=context.env_vars,
                tfvars=config.get('tfvars'),
                working_dir=config.get('working_dir')
            )
            
            artifacts = {}
            if state_path:
                artifacts['state_path'] = state_path
            
            return TaskResult(
                status=TaskStatus.SUCCESS if success else TaskStatus.FAILED,
                output=output,
                error=None if success else output,
                artifacts=artifacts
            )
            
        except Exception as e:
            return TaskResult(
                status=TaskStatus.FAILED,
                output="",
                error=str(e)
            )
    
    def can_retry(self, error: Exception) -> bool:
        """Refresh is idempotent and can be retried."""
        return True
    
    def get_timeout(self) -> int:
        """Refresh operations are typically fast."""
        return 300  # 5 minutes