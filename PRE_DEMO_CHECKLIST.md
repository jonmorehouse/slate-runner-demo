# Pre-Demo Checklist

Complete this checklist before your meetup tomorrow to ensure everything works smoothly.

## ✅ Environment Setup

- [ ] Python 3.9+ installed: `python --version`
- [ ] Terraform installed: `terraform --version`
- [ ] Git installed: `git --version`
- [ ] All dependencies installed (see below)

### Install Control Plane Dependencies
```bash
cd control-plane
pip install -r requirements.txt
cd ..
```

### Install Runner Dependencies
```bash
cd runner
pip install -r requirements.txt
cd ..
```

## ✅ Tigris Configuration

- [ ] Signed up for Tigris account at https://www.tigrisdata.com/
- [ ] Created bucket: `slate-demo-meta`
- [ ] Created bucket: `slate-demo-runner`
- [ ] Have access credentials ready
- [ ] Copied `.env.example` to `.env`
- [ ] Updated `.env` with Tigris credentials:
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_ENDPOINT_URL=https://fly.storage.tigris.dev`

## ✅ Test Control Plane

```bash
cd control-plane
python app.py
```

Expected output:
```
 * Running on http://0.0.0.0:5000
 * Debug mode: on
```

- [ ] Control plane starts without errors
- [ ] Can access http://localhost:5000 in browser
- [ ] Dashboard page loads (shows "No agents")

Stop with `Ctrl+C`

## ✅ Test Runner

```bash
cd runner
python main.py
```

Expected output:
```
[Runner] Registering with control plane
[Runner] ✓ Registered successfully
[HealthCheck] Starting health check loop
[Operations] Starting operations loop
[Jobs] Starting job loop
```

- [ ] Runner starts without errors
- [ ] Registers with control plane
- [ ] All three loops start

Stop with `Ctrl+C`

## ✅ Test End-to-End Flow

### Terminal 1: Start Control Plane
```bash
cd control-plane
python app.py
```

### Terminal 2: Start Runner
```bash
cd runner
python main.py
```

### Browser: Test the System

1. - [ ] Go to http://localhost:5000
2. - [ ] Agent appears in dashboard as "Online"
3. - [ ] Click on agent name to see detail page
4. - [ ] Navigate to Jobs page
5. - [ ] Click "Create Job" button
6. - [ ] Fill in form with test data:
   ```
   Agent: runner-001
   Repository: https://github.com/hashicorp/terraform-provider-null
   Operation: plan
   ```
7. - [ ] Submit job
8. - [ ] Watch job status change: Pending → Running → Completed
9. - [ ] Click on job to see output
10. - [ ] Verify Terraform output is displayed

### Test Agent Controls

- [ ] Go to agent detail page
- [ ] Click "Pause" - verify agent stops processing jobs
- [ ] Create another job - verify it stays "Pending"
- [ ] Click "Resume" - verify job executes
- [ ] All controls work correctly

### Test Offline Detection

- [ ] In Terminal 2, press `Ctrl+C` to stop runner
- [ ] Wait 15-20 seconds
- [ ] Refresh dashboard in browser
- [ ] Agent should show as "Offline"

## ✅ Demo Terraform Repository

Option 1: Use demo-terraform-repo in this project
- [ ] Initialize as git repo
- [ ] Push to GitHub
- [ ] Test with runner using that URL

Option 2: Use existing simple repo
- [ ] Find or create simple Terraform config
- [ ] Ensure it's publicly accessible
- [ ] Test with runner

## ✅ Presentation Prep

- [ ] Browser tabs open and ready:
  - Tab 1: Dashboard (http://localhost:5000)
  - Tab 2: Jobs page (http://localhost:5000/jobs)
- [ ] Terminal windows arranged:
  - Terminal 1: Control plane (visible)
  - Terminal 2: Runner 1 (visible)
  - Terminal 3: Runner 2 (hidden, ready to launch)
- [ ] README.md open for reference
- [ ] DEMO_SCRIPT.md printed or on second screen
- [ ] Backup plan ready (screenshots, curl commands)

## ✅ Multi-Agent Test (Optional but Recommended)

### Terminal 3: Start Second Runner
```bash
RUNNER_ID=runner-002 RUNNER_NAME="Runner 2" python main.py
```

- [ ] Second runner registers successfully
- [ ] Both runners visible in dashboard
- [ ] Can create jobs for each runner
- [ ] Both execute jobs independently

## ✅ Common Issues - Verify Not Present

- [ ] Port 5000 is available (not used by another app)
- [ ] No firewall blocking localhost connections
- [ ] `.env` file exists and has correct values
- [ ] S3 buckets exist and are accessible
- [ ] Terraform is in PATH: `which terraform`
- [ ] No rate limits on Tigris account

## ✅ Performance Check

- [ ] Dashboard loads quickly (< 2 seconds)
- [ ] Real-time updates work (agent list refreshes every 2s)
- [ ] Job execution completes in reasonable time
- [ ] No errors in browser console (F12)
- [ ] No Python exceptions in terminal

## ✅ Backup Materials

- [ ] Screenshots of working demo saved
- [ ] Curl commands tested and ready:
  ```bash
  # Register agent
  curl -X POST http://localhost:5000/api/agents \
    -H "Content-Type: application/json" \
    -d '{"agent_id":"runner-001","name":"Demo"}'
  
  # Create job
  curl -X POST http://localhost:5000/api/jobs \
    -H "Content-Type: application/json" \
    -d '{"agent_id":"runner-001","repo_url":"https://github.com/hashicorp/terraform-provider-null","operation":"plan"}'
  ```
- [ ] Architecture diagram prepared
- [ ] Slide deck ready (if using slides)

## ✅ Day-Of Checklist

Morning of the meetup:

- [ ] Run through entire demo once more
- [ ] Clear S3 buckets (start fresh)
- [ ] Close unnecessary applications
- [ ] Disable notifications
- [ ] Test internet connection
- [ ] Charge laptop fully
- [ ] Bring charger
- [ ] Have this checklist available

## 🎯 Success Criteria

Your demo is ready when:

1. ✅ Control plane starts cleanly
2. ✅ Runner registers and stays online
3. ✅ Jobs execute successfully
4. ✅ UI updates in real-time
5. ✅ Agent controls work
6. ✅ Offline detection works
7. ✅ Multi-agent demo works
8. ✅ You can explain the architecture clearly

## 🚨 Emergency Contacts

If something breaks during setup:

1. Check README.md troubleshooting section
2. Review error messages carefully
3. Verify .env configuration
4. Test S3 connectivity manually
5. Use curl commands as backup demo
6. Have screenshots ready

## 📝 Notes

Use this space for any issues you encounter during testing:

```
Issue 1: 
Solution: 

Issue 2:
Solution:

Issue 3:
Solution:
```

---

**Good luck with your demo! 🚀**

Once you've completed this checklist, you're ready to present!
