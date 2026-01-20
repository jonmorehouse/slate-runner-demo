"""Task abstraction for runner operations."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class TaskType(Enum):
    """Task type enumeration."""
    TERRAFORM_PLAN = "terraform_plan"
    TERRAFORM_APPLY = "terraform_apply"
    TERRAFORM_REFRESH = "terraform_refresh"
    HEALTH_CHECK = "health_check"
    STATE_SYNC = "state_sync"
    CUSTOM = "custom"


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskContext:
    """Context passed to tasks during execution."""
    job_id: str
    task_type: str
    config: Dict[str, Any]
    runner_id: str
    workdir: str
    env_vars: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TaskResult:
    """Result returned by task execution."""
    status: TaskStatus
    output: str
    error: Optional[str] = None
    artifacts: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None


class Task(ABC):
    """
    Abstract base class for all runner tasks.
    
    Each task type must implement:
    - execute(): Main execution logic
    - validate(): Pre-execution validation
    - cleanup(): Post-execution cleanup
    
    Example:
        class MyCustomTask(Task):
            def get_type(self) -> str:
                return "my_custom_task"
            
            def validate(self, context: TaskContext) -> bool:
                return context.config.get('required_field') is not None
            
            def execute(self, context: TaskContext) -> TaskResult:
                # Implementation
                return TaskResult(
                    status=TaskStatus.SUCCESS,
                    output="Task completed"
                )
    """
    
    @abstractmethod
    def get_type(self) -> str:
        """
        Return the task type string.
        This is used for routing jobs to the correct task handler.
        """
        pass
    
    @abstractmethod
    def execute(self, context: TaskContext) -> TaskResult:
        """
        Execute the task with the given context.
        
        Args:
            context: Task execution context with job details
            
        Returns:
            TaskResult with execution status and output
        """
        pass
    
    def validate(self, context: TaskContext) -> bool:
        """
        Validate the task context before execution.
        Override this to add custom validation.
        
        Args:
            context: Task execution context
            
        Returns:
            True if validation passes, False otherwise
        """
        return True
    
    def cleanup(self, context: TaskContext):
        """
        Cleanup after task execution (success or failure).
        Override this for custom cleanup logic.
        
        Args:
            context: Task execution context
        """
        pass
    
    def can_retry(self, error: Exception) -> bool:
        """
        Determine if the task can be retried after failure.
        Override this for custom retry logic.
        
        Args:
            error: The exception that caused failure
            
        Returns:
            True if task can be retried, False otherwise
        """
        return False
    
    def get_timeout(self) -> int:
        """
        Return the maximum execution time in seconds.
        Override this for custom timeout values.
        
        Returns:
            Timeout in seconds (default: 600 = 10 minutes)
        """
        return 600


class TaskRegistry:
    """
    Registry for mapping task type strings to Task implementations.
    
    Usage:
        registry = TaskRegistry()
        registry.register(TerraformPlanTask())
        registry.register(CustomTask())
        
        task = registry.get_task("terraform_plan")
        result = task.execute(context)
    """
    
    def __init__(self):
        """Initialize the task registry."""
        self._tasks: Dict[str, Task] = {}
    
    def register(self, task: Task):
        """
        Register a task implementation.
        
        Args:
            task: Task instance to register
        """
        task_type = task.get_type()
        if task_type in self._tasks:
            raise ValueError(f"Task type '{task_type}' already registered")
        
        self._tasks[task_type] = task
        print(f"[TaskRegistry] Registered task: {task_type}")
    
    def get_task(self, task_type: str) -> Optional[Task]:
        """
        Get a task implementation by type string.
        
        Args:
            task_type: Task type string
            
        Returns:
            Task instance or None if not found
        """
        return self._tasks.get(task_type)
    
    def list_tasks(self) -> list:
        """
        List all registered task types.
        
        Returns:
            List of task type strings
        """
        return list(self._tasks.keys())
    
    def has_task(self, task_type: str) -> bool:
        """
        Check if a task type is registered.
        
        Args:
            task_type: Task type string
            
        Returns:
            True if registered, False otherwise
        """
        return task_type in self._tasks
