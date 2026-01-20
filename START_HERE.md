# 🚀 Slate Runner Demo - Quick Start Guide

## Your System is Ready!

All implementation is complete. Here's how to run the demo:

## Prerequisites Check

Run this first to verify everything is set up:
```bash
./test_demo.sh
```

This checks:
- ✅ Python 3 installed
- ✅ Dependencies installed
- ✅ Environment variables set
- ✅ S3 connectivity working

## Running the Demo

### Step 1: Start Control Plane (Terminal 1)
```bash
cd control-plane
python app.py
```

**Wait for:**
```
* Running on http://0.0.0.0:5000
```

### Step 2: Start Runner (Terminal 2)
```bash
cd runner
python main.py
```

**Wait for:**
```
[Runner] ✓ Registered but waiting for adoption...
[Jobs] ⏳ Waiting for adoption - runner not yet adopted by control plane
```

### Step 3: Adopt the Runner
1. Open browser: **http://localhost:5000**
2. You'll see runner with "⏳ Pending" badge
3. Click on the runner name
4. Click **"✓ Adopt Runner"** button

**Runner console will show:**
```
[Operations] 🎉 Runner has been ADOPTED! Can now execute jobs.
```

### Step 4: Create a Test Job (Terminal 3)
```bash
# Create a terraform plan job
python create_test_job.py plan

# Or create an apply job
python create_test_job.py apply
```

**Note:** Update the `DEMO_REPO` variable in `create_test_job.py` to point to your Terraform repository.

### Step 5: Watch It Work!

**In Runner Console:**
```
[Jobs] 📋 Found pending job: abc-123 (operation: plan)
[Jobs] ✓ Claimed job: abc-123
[Jobs] ⚡ Starting job: abc-123 (operation: plan)
Cloning repository: https://github.com/...
Running terraform init...
Running terraform plan...
[Jobs] ✓ Uploaded state to S3: states/abc-123/terraform.tfstate
[Jobs] ✓ Job abc-123 completed
```

**In Browser:**
- Dashboard updates automatically
- Click "Jobs" to see job details
- Click on job ID to see full output

## What's Implemented

### ✅ API Endpoints
- `POST /api/agents` - Runner registration
- `POST /api/health` - Health checks
- `GET /api/jobs/pending` - Fetch pending jobs
- `POST /api/jobs/<id>/claim` - Atomic job claiming
- `PATCH /api/jobs/<id>` - Update job results
- `POST /api/agents/<id>/adopt` - Adopt runners

### ✅ Runner Features
- Auto-registration on startup
- Adoption workflow (security feature)
- S3 state persistence (tracks job stats)
- Health checks every 5 seconds
- Atomic job claiming (prevents duplicates)
- Terraform execution: plan, apply, refresh

### ✅ Terraform Integration
- Clones git repositories
- Runs terraform init/plan/apply/refresh
- Uploads state files to S3: `states/{job_id}/terraform.tfstate`
- Uploads outputs to S3: `outputs/{job_id}.txt`
- Supports custom tfvars and environment variables

### ✅ UI Features
- Real-time dashboard (updates every 2s)
- Agent status monitoring
- Job execution tracking
- Adoption controls
- Pause/lock/unlock controls

## S3 Storage Structure

```
slate-demo-meta/           # Metadata bucket
├── agents/
│   └── runner-001.json    # Runner info
├── jobs/
│   └── {job-id}.json      # Job metadata
└── health/
    └── runner-001/        # Health check history

slate-demo-runner/         # Runner data bucket
├── states/
│   └── {job-id}/
│       └── terraform.tfstate  # Terraform state
├── outputs/
│   └── {job-id}.txt       # Job outputs
└── runner-state/
    └── runner-001/
        └── state.json     # Runner stats
```

## Testing Multiple Runners

Want to test concurrency? Start multiple runners:

**Terminal 3:**
```bash
cd runner
RUNNER_ID=runner-002 RUNNER_NAME="Runner 2" python main.py
```

**Terminal 4:**
```bash
cd runner
RUNNER_ID=runner-003 RUNNER_NAME="Runner 3" python main.py
```

Then create one job and watch only ONE runner claim it!

## Troubleshooting

### "Runner not adopted" in logs
- Go to http://localhost:5000
- Click on runner
- Click "Adopt Runner" button

### "Job stuck in pending"
- Make sure runner is adopted
- Check runner isn't paused/locked
- Verify runner is online (green badge)

### "Terraform fails"
- Check repo URL is accessible
- Verify you have Terraform installed: `terraform --version`
- Check environment variables for AWS creds (if needed)

### "Cannot connect to S3"
- Verify AWS_ENDPOINT_URL is set
- Check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
- Run `./test_demo.sh` to verify connectivity

## Demo Talking Points

### 1. Auto-Discovery
"When a runner starts, it automatically registers with the control plane and appears in the UI immediately."

### 2. Security First
"New runners must be manually adopted before they can execute jobs. This prevents unauthorized runners from joining."

### 3. Atomic Operations
"Job claiming is atomic - if multiple runners are running, only one will claim each job. No duplicates!"

### 4. State Management
"Terraform state files are automatically uploaded to S3 with the job ID in the path, ensuring complete isolation and traceability."

### 5. Real-time Monitoring
"The dashboard auto-refreshes every 2 seconds, showing live status of all runners and jobs."

## Next Steps After Demo

Once basic flow works, you can:
- [ ] Test with real Terraform configurations
- [ ] Add more runners to show scalability
- [ ] Try pause/lock controls
- [ ] Test job failure scenarios
- [ ] View historical job data
- [ ] Examine S3 bucket contents

## Architecture Overview

```
┌─────────────┐         ┌──────────────┐
│   Browser   │────────▶│Control Plane │
│  (Web UI)   │         │  (Flask API) │
└─────────────┘         └──────┬───────┘
                               │
                               │ REST API
                               │
                        ┌──────▼───────┐
                        │    Runner    │
                        │ (Python App) │
                        └──────┬───────┘
                               │
                     ┌─────────┼─────────┐
                     ▼         ▼         ▼
              ┌─────────┐ ┌─────────┐ ┌─────┐
              │   S3    │ │   Git   │ │ TF  │
              │(Tigris) │ │  Repo   │ │ CLI │
              └─────────┘ └─────────┘ └─────┘
```

## Quick Reference

### Environment Variables
```bash
export AWS_ENDPOINT_URL=https://fly.storage.tigris.dev
export AWS_ACCESS_KEY_ID=tid_...
export AWS_SECRET_ACCESS_KEY=tsec_...
export AWS_REGION=auto
export SLATE_META_BUCKET=slate-demo-meta
export SLATE_RUNNER_BUCKET=slate-demo-runner
```

### URLs
- Control Plane UI: http://localhost:5000
- API Base: http://localhost:5000/api

### Default Values
- Runner ID: `runner-001`
- Runner Name: `Demo Runner`
- Poll Interval: `5 seconds`
- Control Plane Port: `5000`

## Support

If something's not working:
1. Check the console output for errors
2. Verify prerequisites with `./test_demo.sh`
3. Check the DEMO_GUIDE.md for detailed troubleshooting
4. Review runner/control-plane logs

---

**You're all set! Run `./test_demo.sh` then follow the steps above.** 🎉
