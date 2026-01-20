# Meetup Demo Script

A complete walkthrough for presenting the Slate Runner demo at your meetup.

## Pre-Demo Checklist

- [ ] Tigris buckets created and credentials configured
- [ ] Dependencies installed (Python packages, Terraform)
- [ ] `.env` file configured with Tigris credentials
- [ ] Demo Terraform repository available (public GitHub repo)
- [ ] Browser tabs ready:
  - Dashboard (http://localhost:5000)
  - Jobs page (http://localhost:5000/jobs)
- [ ] Terminal windows arranged:
  - Terminal 1: Control plane
  - Terminal 2: Runner 1
  - Terminal 3: Runner 2 (optional)

## Demo Flow (15 minutes)

### Act 1: Introduction (2 min)

**What you're showing:**
"Today I'm demonstrating a distributed infrastructure automation system built with SlateDB and S3. It features a control plane for managing multiple runner agents that execute Terraform operations anywhere."

**Key points:**
- Control plane: Python/Flask with HTMX for real-time UI
- Runners: Autonomous agents with reconciliation loops
- Storage: S3 (Tigris) for state and metadata
- Portable: Agents can run anywhere - EC2, local, containers

### Act 2: Starting the System (3 min)

**Terminal 1 - Start Control Plane:**
```bash
cd control-plane
python app.py
```

**Show output:**
- Flask server starting
- Port 5000
- S3 bucket connections

**Browser - Show Empty Dashboard:**
- Navigate to http://localhost:5000
- "No agents registered yet"

**Terminal 2 - Start First Runner:**
```bash
cd runner
python main.py
```

**Point out the startup:**
```
[Runner] Registering with control plane
[Runner] ✓ Registered successfully
[HealthCheck] Starting health check loop
[Operations] Starting operations loop
[Jobs] Starting job loop
```

**Browser - Refresh Dashboard:**
- Agent appears automatically
- Show "Online" status
- Point out last heartbeat timestamp

### Act 3: Creating and Executing a Job (4 min)

**Browser - Navigate to Jobs:**
- Click "Jobs" in navigation
- Click "Create Job" button

**Fill in the form:**
```
Agent: runner-001
Repository URL: https://github.com/YOUR_USERNAME/terraform-demo
Operation: plan
Environment Variables:
{
  "TF_LOG": "INFO"
}
Terraform Variables:
environment = "demo"
message = "Hello from the meetup!"
instance_count = 2
```

**Click "Create Job"**

**Terminal 2 - Show Runner Activity:**
```
[Jobs] ⚡ Starting job: abc-123
Cloning repository...
Running terraform init...
Running terraform plan...
[Jobs] ✓ Uploaded state to S3
[Jobs] ✓ Job abc-123 completed
```

**Browser - Watch Real-time Updates:**
- Job status changes: Pending → Running → Completed
- Click on the job to see details
- Show Terraform output
- Highlight the state file path in S3

**Key callout:**
"Notice how everything happens automatically - the runner polls for jobs, executes Terraform, and uploads results to S3. No persistent connections needed!"

### Act 4: Agent Controls (2 min)

**Browser - Agent Detail Page:**
- Click on the agent name from dashboard
- Show the control buttons

**Pause the Agent:**
- Click "Pause" button
- Show status update

**Terminal 2:**
```
[Operations] Executing command: pause
[Operations] ✓ Command executed: pause
[Jobs] Skipping - runner state: paused=True
```

**Create Another Job:**
- Go back to Jobs page
- Create new job (same or different config)
- Show it stays in "Pending" status

**Resume the Agent:**
- Go back to agent detail
- Click "Resume"
- Watch job execute immediately

**Key callout:**
"Agents respond to control commands in real-time through their reconciliation loops."

### Act 5: Multiple Agents (2 min)

**Terminal 3 - Start Second Runner:**
```bash
RUNNER_ID=runner-002 RUNNER_NAME="EC2 Runner" python main.py
```

**Browser - Dashboard:**
- Refresh to see second agent
- Both showing "Online"

**Create Jobs for Different Agents:**
- Create job for runner-001
- Create job for runner-002
- Show parallel execution

**Key callout:**
"The system scales horizontally - add as many runners as you need, wherever you need them."

### Act 6: Offline Detection (2 min)

**Terminal 3 - Stop Second Runner:**
- Press Ctrl+C
- Show graceful shutdown

**Browser - Watch Dashboard:**
- Count to 15 seconds
- Agent status changes to "Offline"
- Point out the automatic detection

**Key callout:**
"If a runner goes down, the control plane detects it within 15 seconds based on heartbeat timeout. No hanging connections or stale state."

## Q&A Prompts

**Why S3 for storage?**
- Portable: runners work from anywhere
- Durable: critical state is safe
- Shared: multiple systems can access
- SlateDB provides embedded database semantics on object storage

**Why polling instead of webhooks?**
- Simpler: no complex networking or NAT traversal
- Resilient: automatic reconnection
- Scalable: control plane doesn't track connections
- Portable: works behind firewalls

**Production considerations?**
- Add authentication and RBAC
- Implement job queuing and priorities  
- Support private Git repositories
- Add alerting and monitoring
- Implement job templates and workflows

## Cleanup

```bash
# Stop all processes (Ctrl+C in each terminal)
# Optional: Clear S3 buckets for next demo
```

## Backup Demos

If something goes wrong, have these ready:

1. **Pre-recorded video** of the full demo
2. **Screenshots** of key screens
3. **Curl commands** to demo the API without UI:

```bash
# Register agent
curl -X POST http://localhost:5000/api/agents \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "runner-001", "name": "Demo Runner"}'

# Create job
curl -X POST http://localhost:5000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "runner-001", "repo_url": "...", "operation": "plan"}'

# Check job status
curl http://localhost:5000/api/jobs/<job-id>
```

Good luck with your presentation! 🎉
