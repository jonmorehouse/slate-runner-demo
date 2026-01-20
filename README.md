# Slate Runner Demo

A distributed infrastructure agent system demonstrating SlateDB capabilities with Terraform automation. Features a control plane for managing multiple runner agents that execute Terraform operations.

## Architecture

### Components

1. **Control Plane** - Python/Flask web application with HTMX UI
   - Agent management dashboard
   - Job creation and monitoring
   - Real-time status updates
   - Agent control commands (lock, pause, read-only mode)

2. **Runner Agent** - Python application with reconciliation loops
   - Health check reporting (every 5 seconds)
   - Command fetching and execution
   - Job polling and Terraform execution
   - State synchronization to S3

3. **Storage Layer** - Tigris S3-compatible storage with SlateDB
   - Meta-information bucket: Agents, jobs, health checks, commands
   - Runner bucket: Terraform state files and outputs

## Features

- **Multi-Agent Support**: Register and manage multiple runner agents
- **Online/Offline Detection**: Real-time agent status with 15-second timeout
- **Agent Controls**: Lock, pause, or set agents to read-only mode
- **Terraform Operations**: Plan, apply, and refresh with custom variables
- **Job Scheduling**: Queue jobs with public Git repos, env vars, and tfvars
- **State Management**: Automatic state file storage in S3
- **Real-time Updates**: HTMX-powered live dashboard updates

## Prerequisites

- Python 3.9+
- Terraform CLI installed
- Tigris account (or S3-compatible storage)
- Git

## Setup

### 1. Install Dependencies

```bash
# Control plane
cd control-plane
pip install -r requirements.txt

# Runner
cd ../runner
pip install -r requirements.txt
```

### 2. Configure Tigris Buckets

Sign up for Tigris at https://www.tigrisdata.com/ and create two buckets:

1. `slate-demo-meta` - For control plane metadata
2. `slate-demo-runner` - For runner state and outputs

Get your access credentials from the Tigris dashboard.

### 3. Configure Environment Variables

Copy the example environment file and update with your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```bash
# Tigris Configuration
SLATE_META_BUCKET=slate-demo-meta
SLATE_RUNNER_BUCKET=slate-demo-runner
AWS_ACCESS_KEY_ID=your_tigris_access_key_here
AWS_SECRET_ACCESS_KEY=your_tigris_secret_key_here
AWS_ENDPOINT_URL=https://fly.storage.tigris.dev
AWS_REGION=auto

# Control Plane
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=change-this-in-production

# Runner Configuration
RUNNER_ID=runner-001
RUNNER_NAME=Demo Runner
CONTROL_PLANE_URL=http://localhost:5000
POLL_INTERVAL=5
```

### 4. Start the Control Plane

```bash
cd control-plane
python app.py
```

The control plane will be available at http://localhost:5000

### 5. Start a Runner Agent

In a new terminal:

```bash
cd runner
python main.py
```

The runner will:
- Register with the control plane
- Start health check heartbeats
- Poll for jobs every 5 seconds
- Execute Terraform operations

### 6. Start Additional Runners (Optional)

To demonstrate multi-agent support, start additional runners with different IDs:

```bash
RUNNER_ID=runner-002 RUNNER_NAME="Runner 2" python main.py
```

## Usage

### Creating a Job

1. Go to http://localhost:5000/jobs
2. Click "Create Job"
3. Fill in the form:
   - **Agent**: Select a runner
   - **Repository URL**: Public Git repo with Terraform code
   - **Operation**: plan, apply, or refresh
   - **Environment Variables**: JSON object (optional)
   - **Terraform Variables**: tfvars content (optional)

Example:

```
Repository: https://github.com/your-username/terraform-demo
Operation: plan
Env Vars: {"AWS_REGION": "us-west-2"}
Tfvars: 
instance_type = "t3.micro"
environment = "dev"
```

### Controlling Agents

On the agent detail page, you can:

- **Lock/Unlock**: Prevent agent from executing jobs
- **Pause/Resume**: Temporarily stop job execution
- **Read-Only**: Allow only plan/refresh operations

### Monitoring

- **Dashboard** (`/`): View all agents and their online/offline status
- **Jobs** (`/jobs`): View all jobs across all agents
- **Agent Detail** (`/agents/<id>`): View specific agent with recent jobs
- **Job Detail** (`/jobs/<id>`): View job output and Terraform state

## Demo Script

For your meetup presentation:

1. **Start Control Plane**: Show the empty dashboard
2. **Start First Runner**: Watch it register and appear online
3. **Create a Job**: Use a simple Terraform repo (e.g., null resource)
4. **Watch Execution**: Show real-time status updates
5. **View Results**: Display job output and state file
6. **Control Agent**: Pause the agent, show jobs queuing
7. **Start Second Runner**: Demonstrate multi-agent capability
8. **Offline Detection**: Stop a runner, watch it go offline within 15 seconds
9. **Multiple Jobs**: Queue several jobs across different agents

## Example Terraform Repository

Create a simple demo repo:

```hcl
# main.tf
terraform {
  required_version = ">= 1.0"
}

variable "message" {
  description = "Test message"
  default     = "Hello from Slate Runner!"
}

resource "null_resource" "demo" {
  triggers = {
    message = var.message
    timestamp = timestamp()
  }

  provisioner "local-exec" {
    command = "echo '${var.message}'"
  }
}

output "message" {
  value = var.message
}
```

## Troubleshooting

### Runner Can't Connect to Control Plane

- Check `CONTROL_PLANE_URL` in `.env`
- Ensure control plane is running
- Check firewall settings

### S3/Tigris Errors

- Verify bucket names match in `.env`
- Check AWS credentials are correct
- Confirm endpoint URL is `https://fly.storage.tigris.dev`

### Terraform Execution Fails

- Ensure Terraform CLI is installed: `terraform --version`
- Check repository URL is accessible
- Verify environment variables and tfvars syntax

### Agent Shows Offline

- Check runner process is running
- Verify heartbeat interval (default 5 seconds)
- Control plane times out after 15 seconds without heartbeat

## Architecture Decisions

### Why S3 for State?

- **Portable**: Runners can run anywhere (EC2, local, containers)
- **Shared State**: Multiple runners can access common state
- **Durability**: S3 provides reliable storage for critical state

### Why Polling Instead of Push?

- **Simplicity**: No complex networking or firewall configuration
- **Resilience**: Runners automatically reconnect
- **Scalability**: Control plane doesn't track connections

### Why HTMX?

- **Lightweight**: No heavy JavaScript frameworks
- **Real-time**: Easy polling for live updates
- **Simple**: Clean separation of concerns

## Next Steps

- Add authentication and authorization
- Implement job scheduling and cron
- Add webhook notifications
- Support private Git repositories
- Implement job templates
- Add metrics and monitoring dashboards
- Support for multiple Terraform workspaces

## License

MIT
