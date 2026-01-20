"""Request validation utilities."""
from typing import Tuple, Dict, Any


def validate_required_fields(data: Dict[str, Any], required: list) -> Tuple[bool, str]:
    """Validate required fields are present and non-empty.
    
    Args:
        data: Request data dictionary
        required: List of required field names
        
    Returns:
        (is_valid, error_message)
    """
    if not data:
        return False, "Request body is required"
    
    missing = []
    for field in required:
        if field not in data or data[field] is None or data[field] == '':
            missing.append(field)
    
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"
    
    return True, ""


def validate_job_status(status: str) -> bool:
    """Validate job status is a valid value.
    
    Args:
        status: Status string to validate
        
    Returns:
        True if valid, False otherwise
    """
    valid_statuses = ['pending', 'running', 'completed', 'failed']
    return status in valid_statuses


def validate_repo_url(url: str) -> bool:
    """Basic repo URL validation.
    
    Args:
        url: Repository URL to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not url:
        return False
    return url.startswith(('http://', 'https://', 'git@'))


def validate_operation(operation: str) -> bool:
    """Validate terraform operation type.
    
    Args:
        operation: Operation type to validate
        
    Returns:
        True if valid, False otherwise
    """
    valid_operations = ['plan', 'apply', 'refresh']
    return operation in valid_operations
