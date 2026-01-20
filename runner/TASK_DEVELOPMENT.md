# Task Development Guide

This guide explains how to create custom tasks for the Slate Runner.

## Task System Overview

The runner uses a **task-based execution model** where:

1. **Tasks** are registered with a unique type string (e.g., "terraform_plan", "custom_backup")
2. **Jobs** from the control plane specify a task type via the `operation` field
3. The **TaskRegistry** routes jobs to the correct task implementation
4. **Tasks** execute with a `TaskContext` and return a `TaskResult`

## Quick Start: Creating a Custom Task

### Step 1: Create Your Task Class

```python
# runner/tasks/my_custom_task.py
from task import Task, TaskContext, TaskResult, TaskStatus


class MyCustomTask(Task):
    """Example custom task implementation."""
    
    def get_type(self) -> str:
        """Return the task type string for routing."""
        return "my_custom_operation"  # This matches the 'operation' field in jobs
    
    def validate(self, context: TaskContext) -> bool:
        """Validate the task can be executed."""
        # Check required config fields
        if not context.config.get('required_field'):
            print(f"[MyCustomTask] Missing required_field")
            return False
        
        return True
    
    def execute(self, context: TaskContext) -> TaskResult:
        """Execute the task."""
        print(f"[MyCustomTask] Starting execution for job {context.job_id}")
        
        try:
            # Your implementation here
            config = context.config
            required_field = config['required_field']
            
            # Do work...
            output = f"Processed {required_field}"
            
            # Return success
            return TaskResult(
                status=TaskStatus.SUCCESS,
                output=output,
                metadata={
                    'processed_item': required_field
                }
            )
            
        except Exception as e:
            # Return failure
            return TaskResult(
                status=TaskStatus.FAILED,
                output="",
                error=str(e)
            )
    
    def cleanup(self, context: TaskContext):
        """Cleanup after execution."""
        # Optional: cleanup resources
        print(f"[MyCustomTask] Cleanup complete")
    
    def get_timeout(self) -> int:
        """Return max execution time in seconds."""
        return 300  # 5 minutes
    
    def can_retry(self, error: Exception) -> bool:
        """Determine if task can be retried on failure."""
        return True  # Allow retries
```

### Step 2: Register Your Task

```python
# runner/tasks/__init__.py
from .terraform_task import TerraformPlanTask, TerraformApplyTask, TerraformRefreshTask
from .my_custom_task import MyCustomTask

__all__ = [
    'TerraformPlanTask',
    'TerraformApplyTask', 
    'TerraformRefreshTask',
    'MyCustomTask',  # Add your task
]
```

```python
# runner/loops.py
def _register_tasks(self):
    """Register all available task implementations."""
    # Register Terraform tasks
    self.task_registry.register(TerraformPlanTask())
    self.task_registry.register(TerraformApplyTask())
    self.task_registry.register(TerraformRefreshTask())
    
    # Register custom tasks
    self.task_registry.register(MyCustomTask())
    
    print(f"[TaskRegistry] Registered tasks: {', '.join(self.task_registry.list_tasks())}")
```

### Step 3: Create Jobs Using Your Task

From the control plane, create a job with your task type:

```python
# Via API
curl -X POST http://localhost:5000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "runner-001",
    "repo_url": "https://example.com/ignored-for-custom-task",
    "operation": "my_custom_operation",
    "env_vars": {},
    "metadata": {
      "required_field": "some_value"
    }
  }'
```

Or via the UI by modifying the job creation form to support custom operations.

## TaskContext Reference

When your task executes, it receives a `TaskContext`:

```python
@dataclass
class TaskContext:
    job_id: str                          # Unique job identifier
    task_type: str                       # Task type string
    config: Dict[str, Any]               # Job configuration (repo_url, tfvars, etc.)
    runner_id: str                       # ID of the runner executing this task
    workdir: str                         # Working directory path
    env_vars: Optional[Dict[str, str]]   # Environment variables
    metadata: Optional[Dict[str, Any]]   # Additional metadata
```

**Access config fields:**
```python
def execute(self, context: TaskContext) -> TaskResult:
    repo_url = context.config.get('repo_url')
    custom_param = context.config.get('custom_param')
    
    # Use env vars
    if context.env_vars:
        for key, value in context.env_vars.items():
            os.environ[key] = value
```

## TaskResult Reference

Your task must return a `TaskResult`:

```python
@dataclass
class TaskResult:
    status: TaskStatus                   # SUCCESS, FAILED, CANCELLED
    output: str                          # Task output/logs
    error: Optional[str] = None          # Error message if failed
    artifacts: Optional[Dict[str, str]]  # Paths to generated files
    metadata: Optional[Dict[str, Any]]   # Additional metadata
```

**Examples:**

```python
# Success with artifacts
return TaskResult(
    status=TaskStatus.SUCCESS,
    output="Backup completed successfully",
    artifacts={
        'backup_file': '/tmp/backup.tar.gz',
        'checksum_file': '/tmp/backup.sha256'
    },
    metadata={
        'size_bytes': 1024000,
        'timestamp': datetime.now().isoformat()
    }
)

# Failure with error
return TaskResult(
    status=TaskStatus.FAILED,
    output="",
    error="Connection timeout to remote server"
)
```

## Advanced Task Examples

### Example 1: Database Backup Task

```python
from task import Task, TaskContext, TaskResult, TaskStatus
import subprocess


class DatabaseBackupTask(Task):
    """Backup a database to S3."""
    
    def get_type(self) -> str:
        return "database_backup"
    
    def validate(self, context: TaskContext) -> bool:
        required = ['db_host', 'db_name', 'backup_bucket']
        return all(context.config.get(field) for field in required)
    
    def execute(self, context: TaskContext) -> TaskResult:
        config = context.config
        
        # Create backup
        backup_file = f"/tmp/{config['db_name']}-{context.job_id}.sql"
        
        cmd = [
            'pg_dump',
            '-h', config['db_host'],
            '-d', config['db_name'],
            '-f', backup_file
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return TaskResult(
                    status=TaskStatus.FAILED,
                    output=result.stderr,
                    error="pg_dump failed"
                )
            
            # Upload to S3 (use self.s3_client)
            # ... upload logic ...
            
            return TaskResult(
                status=TaskStatus.SUCCESS,
                output=f"Backed up {config['db_name']}",
                artifacts={'backup_file': backup_file}
            )
            
        except Exception as e:
            return TaskResult(
                status=TaskStatus.FAILED,
                output="",
                error=str(e)
            )
    
    def get_timeout(self) -> int:
        return 1800  # 30 minutes for large databases
```

### Example 2: Docker Image Build Task

```python
class DockerBuildTask(Task):
    """Build and push a Docker image."""
    
    def get_type(self) -> str:
        return "docker_build"
    
    def validate(self, context: TaskContext) -> bool:
        required = ['repo_url', 'image_name']
        return all(context.config.get(field) for field in required)
    
    def execute(self, context: TaskContext) -> TaskResult:
        config = context.config
        
        # Clone repo
        import git
        repo_path = f"{context.workdir}/repo"
        git.Repo.clone_from(config['repo_url'], repo_path)
        
        # Build image
        image_name = config['image_name']
        tag = config.get('tag', 'latest')
        
        build_cmd = f"docker build -t {image_name}:{tag} {repo_path}"
        
        try:
            result = subprocess.run(
                build_cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return TaskResult(
                    status=TaskStatus.FAILED,
                    output=result.stderr,
                    error="Docker build failed"
                )
            
            # Push if requested
            if config.get('push', False):
                push_cmd = f"docker push {image_name}:{tag}"
                subprocess.run(push_cmd, shell=True, check=True)
            
            return TaskResult(
                status=TaskStatus.SUCCESS,
                output=result.stdout,
                metadata={
                    'image': f"{image_name}:{tag}",
                    'pushed': config.get('push', False)
                }
            )
            
        except Exception as e:
            return TaskResult(
                status=TaskStatus.FAILED,
                output="",
                error=str(e)
            )
    
    def cleanup(self, context: TaskContext):
        """Clean up cloned repo."""
        import shutil
        repo_path = f"{context.workdir}/repo"
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path)
```

### Example 3: HTTP Webhook Task

```python
class WebhookTask(Task):
    """Send a webhook notification."""
    
    def get_type(self) -> str:
        return "webhook"
    
    def validate(self, context: TaskContext) -> bool:
        return context.config.get('webhook_url') is not None
    
    def execute(self, context: TaskContext) -> TaskResult:
        import requests
        
        config = context.config
        webhook_url = config['webhook_url']
        
        payload = {
            'job_id': context.job_id,
            'runner_id': context.runner_id,
            'data': config.get('payload', {}),
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=30
            )
            
            if response.status_code >= 400:
                return TaskResult(
                    status=TaskStatus.FAILED,
                    output=response.text,
                    error=f"HTTP {response.status_code}"
                )
            
            return TaskResult(
                status=TaskStatus.SUCCESS,
                output=f"Webhook sent successfully: {response.status_code}",
                metadata={'status_code': response.status_code}
            )
            
        except Exception as e:
            return TaskResult(
                status=TaskStatus.FAILED,
                output="",
                error=str(e)
            )
    
    def can_retry(self, error: Exception) -> bool:
        """Retry on network errors."""
        return isinstance(error, (requests.Timeout, requests.ConnectionError))
    
    def get_timeout(self) -> int:
        return 60  # 1 minute
```

## Task Lifecycle

```
1. Job received from control plane
   ↓
2. TaskRegistry.get_task(operation) → finds Task implementation
   ↓
3. Task.validate(context) → checks if task can run
   ↓
4. Task.execute(context) → performs work
   ↓
5. Task.cleanup(context) → cleanup (always runs)
   ↓
6. Result uploaded to control plane and S3
```

## Best Practices

### 1. **Idempotency**
Make tasks idempotent when possible:
```python
def execute(self, context: TaskContext) -> TaskResult:
    # Check if already done
    if self._already_completed(context):
        return TaskResult(
            status=TaskStatus.SUCCESS,
            output="Already completed"
        )
    
    # Do work...
```

### 2. **Progress Logging**
Use print statements for progress:
```python
def execute(self, context: TaskContext) -> TaskResult:
    print(f"[MyTask] Step 1: Downloading...")
    # work
    
    print(f"[MyTask] Step 2: Processing...")
    # work
    
    print(f"[MyTask] Step 3: Uploading...")
    # work
```

### 3. **Error Handling**
Catch specific exceptions:
```python
def execute(self, context: TaskContext) -> TaskResult:
    try:
        # work
        return TaskResult(status=TaskStatus.SUCCESS, ...)
    except FileNotFoundError as e:
        return TaskResult(
            status=TaskStatus.FAILED,
            error=f"File not found: {e.filename}"
        )
    except PermissionError as e:
        return TaskResult(
            status=TaskStatus.FAILED,
            error=f"Permission denied: {e}"
        )
```

### 4. **Cleanup Resources**
Always cleanup in the cleanup method:
```python
def cleanup(self, context: TaskContext):
    """Cleanup is called even if execute fails."""
    if hasattr(self, 'temp_file') and os.path.exists(self.temp_file):
        os.remove(self.temp_file)
    
    if hasattr(self, 'connection'):
        self.connection.close()
```

### 5. **Timeouts**
Set appropriate timeouts:
```python
def get_timeout(self) -> int:
    # Short tasks
    return 60      # 1 minute
    
    # Medium tasks  
    return 600     # 10 minutes
    
    # Long tasks
    return 3600    # 1 hour
```

## Testing Tasks

Create a test script:

```python
# test_my_task.py
from task import TaskContext, TaskStatus
from tasks.my_custom_task import MyCustomTask


def test_my_task():
    task = MyCustomTask()
    
    context = TaskContext(
        job_id="test-123",
        task_type="my_custom_operation",
        config={
            'required_field': 'test_value'
        },
        runner_id="test-runner",
        workdir="/tmp/test",
        env_vars={},
        metadata={}
    )
    
    # Test validation
    assert task.validate(context) == True
    
    # Test execution
    result = task.execute(context)
    assert result.status == TaskStatus.SUCCESS
    
    # Test cleanup
    task.cleanup(context)
    
    print("✓ All tests passed")


if __name__ == '__main__':
    test_my_task()
```

Run tests:
```bash
cd runner
python test_my_task.py
```

## Summary

To add a new task type:

1. ✅ Create a class that inherits from `Task`
2. ✅ Implement `get_type()` with a unique string
3. ✅ Implement `execute()` with your logic
4. ✅ Override `validate()`, `cleanup()`, `get_timeout()` as needed
5. ✅ Register the task in `loops.py`
6. ✅ Create jobs with your task's `operation` type

The task system provides:
- ✅ Clean separation of concerns
- ✅ Easy extensibility
- ✅ Type-based routing
- ✅ Standardized error handling
- ✅ Resource cleanup guarantees
- ✅ Timeout management
- ✅ Retry logic

Happy task development! 🚀
