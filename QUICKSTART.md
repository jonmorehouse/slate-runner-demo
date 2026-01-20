# Quick Start Guide

Get the Slate Runner demo running in 5 minutes!

## Prerequisites

- Python 3.9+
- Terraform installed: `brew install terraform` (macOS) or download from terraform.io
- Tigris account (free at https://www.tigrisdata.com/)

## Setup Steps

### 1. Clone and Install Dependencies

```bash
# Install control plane dependencies
cd control-plane
pip install -r requirements.txt
cd ..

# Install runner dependencies
cd runner
pip install -r requirements.txt
cd ..
```

### 2. Configure Tigris

```bash
# Sign up at https://www.tigrisdata.com/
# Create two buckets:
# - slate-demo-meta
# - slate-demo-runner

# Get your credentials from the Tigris dashboard
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your Tigris credentials:
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY
```

### 4. Start the System

**Terminal 1 - Control Plane:**
```bash
cd control-plane
python app.py
```

**Terminal 2 - Runner:**
```bash
cd runner
python main.py
```

### 5. Access the Dashboard

Open http://localhost:5000 in your browser!

## Create Your First Job

1. Go to http://localhost:5000/jobs
2. Click "Create Job"
3. Use this example:

```
Agent: runner-001
Repository URL: https://github.com/hashicorp/terraform-provider-null
Operation: plan
Env Vars: {}
Tfvars: (leave empty)
```

Or create a simple test repo with:

**main.tf:**
```hcl
resource "null_resource" "test" {
  provisioner "local-exec" {
    command = "echo 'Hello from Slate Runner!'"
  }
}
```

## Demo Flow

1. **Watch Agent Register**: See runner appear as "Online" in dashboard
2. **Create a Job**: Submit a Terraform plan job
3. **Monitor Execution**: Watch real-time status updates
4. **View Results**: Check job output and Terraform state
5. **Control Agent**: Try pausing the agent
6. **Offline Detection**: Stop the runner, watch it go offline in ~15 seconds
7. **Multiple Runners**: Start a second runner with different ID:
   ```bash
   RUNNER_ID=runner-002 RUNNER_NAME="Runner 2" python main.py
   ```

## Troubleshooting

**Port 5000 already in use?**
```bash
# Change port in control-plane
PORT=8000 python app.py

# Update runner config
CONTROL_PLANE_URL=http://localhost:8000 python main.py
```

**Can't connect to Tigris?**
- Verify credentials in `.env`
- Check endpoint: `https://fly.storage.tigris.dev`
- Test with: `aws s3 ls --endpoint-url=$AWS_ENDPOINT_URL`

**Terraform not found?**
```bash
# macOS
brew install terraform

# Linux
wget https://releases.hashicorp.com/terraform/1.6.6/terraform_1.6.6_linux_amd64.zip
unzip terraform_1.6.6_linux_amd64.zip
sudo mv terraform /usr/local/bin/
```

## Next Steps

- Create more complex Terraform configurations
- Try different operations (plan, apply, refresh)
- Experiment with agent controls (lock, pause, read-only)
- Run multiple runners simultaneously
- Monitor the S3 buckets to see stored state files

Enjoy your demo! 🚀
