"""Main runner application with FX-style lifecycle."""
import os
import sys
import signal
import threading
import requests
from datetime import datetime
from dotenv import load_dotenv
from config import RunnerConfig
from loops import RunnerLoops
from state import RunnerStateManager

# Load environment variables
load_dotenv()


class Runner:
    """Main runner application."""
    
    def __init__(self):
        """Initialize runner."""
        self.config = RunnerConfig.from_env()
        self.state = RunnerStateManager(self.config.runner_id)
        self.loops = RunnerLoops(self.config, self.state)
        self.threads = []
    
    def register(self) -> bool:
        """Register with control plane."""
        print(f"[Runner] Registering with control plane: {self.config.control_plane_url}")
        
        try:
            payload = {
                'agent_id': self.config.runner_id,
                'name': self.config.runner_name,
                'adopted': False,
                'metadata': {
                    'version': '1.0.0',
                    'platform': sys.platform,
                    'state_bucket': os.getenv('SLATE_RUNNER_BUCKET', 'slate-demo-runner')
                }
            }
            
            response = requests.post(
                f"{self.config.control_plane_url}/api/agents",
                json=payload,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                agent_data = response.json()
                if agent_data.get('adopted'):
                    print(f"[Runner] ✓ Registered and ADOPTED")
                else:
                    print(f"[Runner] ✓ Registered but waiting for adoption...")
                return True
            else:
                print(f"[Runner] ✗ Registration failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"[Runner] ✗ Registration error: {e}")
            return False
    
    def start(self):
        """Start all reconciliation loops."""
        print(f"\n{'='*60}")
        print(f"Starting Slate Runner")
        print(f"{'='*60}")
        print(f"Runner ID: {self.config.runner_id}")
        print(f"Runner Name: {self.config.runner_name}")
        print(f"Control Plane: {self.config.control_plane_url}")
        print(f"Poll Interval: {self.config.poll_interval}s")
        print(f"{'='*60}\n")
        
        # Register with control plane
        if not self.register():
            print("[Runner] Failed to register. Exiting.")
            return
        
        # Save initial state
        self.state.set('started_at', datetime.utcnow().isoformat())
        self.state.save()
        
        # Start all loops in separate threads
        loop_functions = [
            ('HealthCheck', self.loops.health_check_loop),
            ('Operations', self.loops.operations_loop),
            ('Jobs', self.loops.job_loop),
        ]
        
        for name, loop_func in loop_functions:
            thread = threading.Thread(target=loop_func, name=name, daemon=True)
            thread.start()
            self.threads.append(thread)
            print(f"[Runner] Started {name} thread")
        
        print(f"\n[Runner] All loops running. Press Ctrl+C to stop.\n")
        
        # Keep main thread alive
        try:
            while True:
                for thread in self.threads:
                    thread.join(timeout=1.0)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the runner gracefully."""
        print("\n[Runner] Shutdown signal received")
        self.loops.stop()
        
        # Wait for threads to finish
        for thread in self.threads:
            thread.join(timeout=5.0)
        
        print("[Runner] ✓ Shutdown complete")


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    print("\n[Runner] Received signal, shutting down...")
    sys.exit(0)


if __name__ == '__main__':
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start runner
    runner = Runner()
    runner.start()