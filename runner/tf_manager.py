"""Terraform version manager - downloads and manages Terraform binaries."""
import os
import platform
import zipfile
import requests
from pathlib import Path
from typing import Optional


class TerraformVersionManager:
    """Manages Terraform binary versions."""
    
    def __init__(self, install_dir: Optional[str] = None, version: Optional[str] = None):
        """Initialize the version manager.
        
        Args:
            install_dir: Directory to install Terraform binaries (default: /tmp/terraform-versions)
            version: Terraform version to use (default: from TF_VERSION env var or 1.14.3)
        """
        self.install_dir = install_dir or os.getenv('TF_INSTALL_DIR', '/tmp/terraform-versions')
        self.version = version or os.getenv('TF_VERSION', '1.14.3')
        self.binary_path = self._get_binary_path()
        
        # Create install directory if it doesn't exist
        Path(self.install_dir).mkdir(parents=True, exist_ok=True)
    
    def _get_binary_path(self) -> str:
        """Get the path to the terraform binary for this version."""
        version_dir = os.path.join(self.install_dir, self.version)
        return os.path.join(version_dir, 'terraform')
    
    def _get_download_url(self) -> str:
        """Get the download URL for the current platform and version."""
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        # Map platform names to Terraform's naming convention
        os_name = {
            'darwin': 'darwin',
            'linux': 'linux',
            'windows': 'windows'
        }.get(system, system)
        
        # Map architecture names
        arch = {
            'x86_64': 'amd64',
            'amd64': 'amd64',
            'arm64': 'arm64',
            'aarch64': 'arm64'
        }.get(machine, 'amd64')
        
        filename = f"terraform_{self.version}_{os_name}_{arch}.zip"
        return f"https://releases.hashicorp.com/terraform/{self.version}/{filename}"
    
    def ensure_installed(self) -> str:
        """Ensure Terraform is installed, download if necessary.
        
        Returns:
            Path to the terraform binary
        """
        if os.path.exists(self.binary_path) and os.access(self.binary_path, os.X_OK):
            print(f"[TF Manager] Terraform {self.version} already installed at {self.binary_path}")
            return self.binary_path
        
        print(f"[TF Manager] Terraform {self.version} not found, downloading...")
        return self._download_and_install()
    
    def _download_and_install(self) -> str:
        """Download and install Terraform."""
        url = self._get_download_url()
        version_dir = os.path.join(self.install_dir, self.version)
        Path(version_dir).mkdir(parents=True, exist_ok=True)
        
        zip_path = os.path.join(version_dir, 'terraform.zip')
        
        try:
            # Download the zip file
            print(f"[TF Manager] Downloading from {url}")
            response = requests.get(url, stream=True, timeout=120)
            response.raise_for_status()
            
            # Save to disk
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"[TF Manager] Downloaded to {zip_path}")
            
            # Extract the zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(version_dir)
            
            # Make binary executable
            os.chmod(self.binary_path, 0o755)
            
            # Clean up zip file
            os.remove(zip_path)
            
            print(f"[TF Manager] Terraform {self.version} installed successfully")
            return self.binary_path
            
        except Exception as e:
            print(f"[TF Manager] Error installing Terraform: {e}")
            raise
    
    def get_binary_path(self) -> str:
        """Get the path to the terraform binary, installing if necessary."""
        return self.ensure_installed()