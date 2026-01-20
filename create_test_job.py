#!/usr/bin/env python3
"""
Quick script to create a test Terraform job.
Usage: python create_test_job.py [plan|apply|refresh]
"""

import sys
import requests
import json

CONTROL_PLANE_URL = "http://localhost:5000"
RUNNER_ID = "runner-001"

# Use the demo repo from the project
DEMO_REPO = "https://github.com/nuon-dev/demo-terraform-repo"  # Update this to your actual demo repo

def create_job(operation="plan"):
    """Create a test job."""
    
    payload = {
        "agent_id": RUNNER_ID,
        "repo_url": DEMO_REPO,
        "operation": operation,
        "env_vars": {
            # Add any required Terraform env vars here
            # "AWS_REGION": "us-west-2"
        }
    }
    
    print(f"Creating {operation} job...")
    print(f"Repo: {DEMO_REPO}")
    print(f"Runner: {RUNNER_ID}")
    print()
    
    try:
        response = requests.post(
            f"{CONTROL_PLANE_URL}/api/jobs",
            json=payload,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            job = response.json()
            print("✅ Job created successfully!")
            print(f"Job ID: {job['job_id']}")
            print(f"Status: {job['status']}")
            print(f"Operation: {job['operation']}")
            print()
            print(f"View in UI: {CONTROL_PLANE_URL}/jobs/{job['job_id']}")
            return job
        else:
            print(f"❌ Failed to create job: {response.status_code}")
            print(response.text)
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to control plane.")
        print(f"Is it running at {CONTROL_PLANE_URL}?")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def check_runner_adopted():
    """Check if runner is adopted."""
    try:
        response = requests.get(
            f"{CONTROL_PLANE_URL}/api/agents/{RUNNER_ID}",
            timeout=10
        )
        
        if response.status_code == 200:
            agent = response.json()
            if agent.get('adopted'):
                print(f"✅ Runner {RUNNER_ID} is adopted")
                return True
            else:
                print(f"⚠️  Runner {RUNNER_ID} is NOT adopted yet")
                print(f"   Adopt at: {CONTROL_PLANE_URL}/agents/{RUNNER_ID}")
                return False
        else:
            print(f"❌ Runner {RUNNER_ID} not found")
            print("   Make sure the runner is running")
            return False
            
    except Exception as e:
        print(f"❌ Could not check runner status: {e}")
        return False

if __name__ == "__main__":
    operation = sys.argv[1] if len(sys.argv) > 1 else "plan"
    
    if operation not in ["plan", "apply", "refresh"]:
        print(f"Invalid operation: {operation}")
        print("Usage: python create_test_job.py [plan|apply|refresh]")
        sys.exit(1)
    
    print("=" * 60)
    print("Slate Runner - Create Test Job")
    print("=" * 60)
    print()
    
    # Check if runner is adopted
    if not check_runner_adopted():
        print()
        print("⚠️  Warning: Runner is not adopted. Job will not execute.")
        print()
    
    # Create job
    job = create_job(operation)
    
    if job:
        print()
        print("=" * 60)
        print("Next steps:")
        print("  1. Watch runner console for job execution")
        print(f"  2. View job in UI: {CONTROL_PLANE_URL}/jobs")
        print("=" * 60)
