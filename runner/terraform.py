"""Terraform execution logic."""
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple
from git import Repo
from tf_manager import TerraformVersionManager


class TerraformExecutor:
    """Executes Terraform operations."""
    
    def __init__(self, workdir: str = None, tf_version: Optional[str] = None):
        """Initialize executor.
        
        Args:
            workdir: Base working directory for terraform operations
            tf_version: Specific Terraform version to use (overrides env var)
        """
        self.workdir = workdir or tempfile.mkdtemp(prefix='terraform-')
        
        # Initialize Terraform version manager
        self.tf_manager = TerraformVersionManager(version=tf_version)
        self.terraform_bin = self.tf_manager.ensure_installed()
        print(f"[TerraformExecutor] Using Terraform binary: {self.terraform_bin}")
    
    def execute_job(
        self,
        repo_url: str,
        operation: str,
        env_vars: Optional[Dict[str, str]] = None,
        tfvars: Optional[str] = None,
        working_dir: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Execute a Terraform job.
        
        Args:
            repo_url: Git repository URL
            operation: Terraform operation (plan/apply/refresh)
            env_vars: Environment variables for terraform
            tfvars: Contents of terraform.tfvars file
            working_dir: Subdirectory within repo to run terraform in
        
        Returns:
            Tuple of (success, output, state_file_path)
        """
        job_dir = None
        try:
            # Create unique directory for this job
            job_dir = tempfile.mkdtemp(dir=self.workdir)
            
            # Clone repository
            print(f"Cloning repository: {repo_url}")
            Repo.clone_from(repo_url, job_dir)
            
            # Determine terraform working directory
            tf_dir = job_dir
            if working_dir:
                tf_dir = os.path.join(job_dir, working_dir.lstrip('/'))
                if not os.path.exists(tf_dir):
                    return False, f"Working directory not found in repo: {working_dir}", None
                print(f"Using working directory: {working_dir}")
            
            # Write tfvars file if provided
            if tfvars:
                tfvars_path = os.path.join(tf_dir, 'terraform.tfvars')
                with open(tfvars_path, 'w') as f:
                    f.write(tfvars)
                print(f"Wrote terraform.tfvars")
            
            # Prepare environment
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)
            
            # Initialize Terraform
            print("Running terraform init...")
            init_result = self._run_terraform_command(
                [self.terraform_bin, 'init', '-no-color'],
                cwd=tf_dir,
                env=env
            )
            
            if not init_result[0]:
                return False, f"Init failed:\n{init_result[1]}", None
            
            output = f"=== Terraform Init ===\n{init_result[1]}\n\n"
            
            # Run the requested operation
            if operation == 'plan':
                print("Running terraform plan...")
                plan_result = self._run_terraform_command(
                    [self.terraform_bin, 'plan', '-no-color'],
                    cwd=tf_dir,
                    env=env
                )
                output += f"=== Terraform Plan ===\n{plan_result[1]}\n"
                success = plan_result[0]
                
            elif operation == 'apply':
                print("Running terraform apply...")
                apply_result = self._run_terraform_command(
                    [self.terraform_bin, 'apply', '-auto-approve', '-no-color'],
                    cwd=tf_dir,
                    env=env
                )
                output += f"=== Terraform Apply ===\n{apply_result[1]}\n"
                success = apply_result[0]
                
            elif operation == 'refresh':
                print("Running terraform refresh...")
                refresh_result = self._run_terraform_command(
                    [self.terraform_bin, 'refresh', '-no-color'],
                    cwd=tf_dir,
                    env=env
                )
                output += f"=== Terraform Refresh ===\n{refresh_result[1]}\n"
                success = refresh_result[0]
            else:
                return False, f"Unknown operation: {operation}", None
            
            # Get state file if it exists
            state_file = os.path.join(tf_dir, 'terraform.tfstate')
            state_path = state_file if os.path.exists(state_file) else None
            
            return success, output, state_path
            
        except Exception as e:
            error_msg = f"Error executing Terraform job: {str(e)}"
            print(error_msg)
            return False, error_msg, None
        
        finally:
            # Cleanup is handled by the caller to allow state file upload
            pass
    
    def _run_terraform_command(
        self,
        cmd: list,
        cwd: str,
        env: Dict[str, str],
        timeout: int = 300
    ) -> Tuple[bool, str]:
        """Run a terraform command and return success status and output."""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\n{result.stderr}"
            
            return result.returncode == 0, output
            
        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, f"Error running command: {str(e)}"
    
    def cleanup(self):
        """Cleanup working directory."""
        if self.workdir and os.path.exists(self.workdir):
            try:
                shutil.rmtree(self.workdir)
                print(f"Cleaned up workdir: {self.workdir}")
            except Exception as e:
                print(f"Error cleaning up workdir: {e}")