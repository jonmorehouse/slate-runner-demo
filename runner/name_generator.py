"""Generate random names for runners."""
import random
import uuid

ADJECTIVES = [
    'swift', 'brave', 'clever', 'mighty', 'noble', 'eager', 'quick', 'wise',
    'bold', 'keen', 'agile', 'bright', 'calm', 'daring', 'fierce', 'gentle',
    'happy', 'jolly', 'lively', 'merry', 'nimble', 'proud', 'quiet', 'steady'
]

NOUNS = [
    'falcon', 'tiger', 'eagle', 'lion', 'wolf', 'hawk', 'bear', 'fox',
    'owl', 'deer', 'shark', 'dragon', 'phoenix', 'raven', 'thunder', 'storm',
    'comet', 'star', 'rocket', 'arrow', 'blade', 'shield', 'hammer', 'anchor'
]

def generate_runner_name() -> str:
    """Generate a random runner name like 'brave-falcon'.
    
    Returns:
        Generated name string in format 'adjective-noun'
    """
    adj = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)
    return f"{adj}-{noun}"


def generate_runner_id(prefix: str = 'runner') -> str:
    """Generate a unique runner ID like 'runner-abc12345'.
    
    Args:
        prefix: Prefix for the ID (default: 'runner')
        
    Returns:
        Generated ID string in format 'prefix-shortid'
    """
    short_id = str(uuid.uuid4())[:8]
    return f"{prefix}-{short_id}"
