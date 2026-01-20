# Slate Runner Demo Guide

## System Overview

Your demo system is **fully implemented** and ready to test!

### What's Working:

✅ **API Endpoints:**
- Health checks: `POST /api/health`
- Job fetching: `GET /api/jobs/pending`
- Job claiming: `POST /api/jobs/<id>/claim`
- Job results: `PATCH /api/jobs/<id>`
- Runner adoption: `POST /api/agents/<id>/adopt`

✅ **Runner Features:**
- Auto-registration on startup
- Adoption workflow (must be adopted to work)
- S3 state persistence
- Terraform execution (plan, apply, refresh)
- State file upload to S3

✅ **Terraform Jobs:**
- `plan` - Preview changes
- `apply` - Apply infrastructure
- `refresh` - Sync state

## Running the Demo

### Prerequisites:
```bash
# Ensure you have these environment variables set
export AWS_ENDPOINT_URL=<your-tigris-url>
export AWS_ACCESS_KEY_ID=<your-key>
export AWS_SECRET_ACCESS_KEY=<your-secret>
export AWS_REGION=auto
export SLATE_META_BUCKET=slate-demo-meta
export SLATE_RUNNER_BUCKET=slate-demo-runner
```

### Step 1: Start Control Plane
```bash
cd control-plane
python app.py
```

**Expected output:**
```
* Running on http://0.0.0.0:5000
```

### Step 2: Start Runner
```bash
cd runner
python main.py
```

**Expected output:**
```
============================================================
Starting Slate Runner
============================================================
Runner ID: runner-001
Runner Name: Demo Runner
Control Plane: http://localhost:5000
Poll Interval: 5s
============================================================

[Runner] ✓ Registered but waiting for adoption...
[Runner] Started HealthCheck thread
[Runner] Started Operations thread
[Runner] Started Jobs thread

[Jobs] ⏳ Waiting for adoption - runner not yet adopted by control plane
[HealthCheck] ✓ Heartbeat sent (CPU: 5.2%, MEM: 45.3%)
```

### Step 3: Adopt Runner in UI

1. Open browser: http://localhost:5000
2. See runner with "⏳ Pending" badge
3. Click on runner name
4. Click "✓ Adopt Runner" button

**Runner console will show:**
```
[Operations] 🎉 Runner has been ADOPTED! Can now execute jobs.
```

### Step 4: Create a Test Job

Using curl or the API:

```bash
# Create a terraform plan job
curl -X POST http://localhost:5000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "runner-001",
    "repo_url": "https://github.com/your-org/demo-terraform-repo",
    "operation": "plan"
  }'
```

**Or via Python:**
```python
import requests

response = requests.post('http://localhost:5000/api/jobs', json={
    'agent_id': 'runner-001',
    'repo_url': 'https://github.com/your-org/demo-terraform-repo',
    'operation': 'plan'
})
print(response.json())
```

### Step 5: Watch Job Execute

**Runner console:**
```
[Jobs] 📋 Found pending job: abc-123-def (operation: plan)
[Jobs] ✓ Claimed job: abc-123-def
[Jobs] ⚡ Starting job: abc-123-def (operation: plan)
Cloning repository: https://github.com/...
Running terraform init...
Running terraform plan...
[Jobs] ✓ Uploaded state to S3: states/abc-123-def/terraform.tfstate
[Jobs] ✓ Uploaded output to S3
[Jobs] ✓ Job abc-123-def completed
```

### Step 6: Check Results

**In UI:**
- Go to http://localhost:5000/jobs
- Click on the completed job
- See the terraform output

**In S3:**
```
Bucket: slate-demo-runner
- states/abc-123-def/terraform.tfstate
- outputs/abc-123-def.txt

Bucket: slate-demo-meta
- agents/runner-001.json
- jobs/abc-123-def.json
```

## Demo Talking Points

### 1. Runner Registration
"When the runner starts, it automatically registers with the control plane but cannot execute jobs yet."

### 2. Adoption Workflow
"For security, new runners must be manually adopted before they can execute jobs. This prevents rogue runners from joining."

### 3. Job Execution
"Jobs are claimed atomically, so multiple runners won't execute the same job. The runner clones the repo, runs Terraform, and uploads results to S3."

### 4. State Management
"Terraform state files are stored in S3 with the job ID in the path, ensuring isolation and traceability."

### 5. Observability
"The control plane shows real-time status of runners and jobs, with health checks every 5 seconds."

## S3 Storage Schema

```
slate-demo-meta/
├── agents/{runner_id}.json          # Runner registration data
├── jobs/{job_id}.json                # Job metadata
├── health/{runner_id}/{timestamp}.json
└── commands/{command_id}.json

slate-demo-runner/
├── states/{job_id}/terraform.tfstate # Terraform state files
├── outputs/{job_id}.txt              # Job outputs
└── runner-state/{runner_id}/state.json  # Runner state
```

## Troubleshooting

### Runner won't execute jobs
- Check adoption status: Must show "✓ Adopted" in UI
- Check runner console for errors
- Verify S3 credentials are correct

### Jobs stuck in pending
- Ensure runner is adopted
- Check if runner is paused/locked
- Verify runner is online (heartbeat)

### Terraform fails
- Check repo URL is accessible
- Verify environment variables (AWS creds for Terraform)
- Look at job output in UI

## Next Steps

After basic demo works:
- Try creating multiple runners
- Test job concurrency (multiple runners, one job)
- Test pause/lock/unlock controls
- Try apply operation (creates real infrastructure!)

## API Reference

### Create Job
```bash
POST /api/jobs
{
  "agent_id": "runner-001",
  "repo_url": "https://github.com/...",
  "operation": "plan|apply|refresh",
  "env_vars": {"KEY": "value"},
  "tfvars": "var1 = \"value\"\n"
}
```

### Get Job Status
```bash
GET /api/jobs/{job_id}
```

### Adopt Runner
```bash
POST /api/agents/{agent_id}/adopt
```

### Health Check
```bash
POST /api/health
{
  "agent_id": "runner-001",
  "cpu_percent": 5.2,
  "memory_percent": 45.3,
  "disk_percent": 60.1,
  "capabilities": {
    "tasks": ["plan", "apply", "refresh"],
    "version": "1.0.0"
  }
}
```
