# Demo Terraform Repository

This is a simple Terraform configuration for demonstrating the Slate Runner system.

## What It Does

This configuration creates:
- Null resources that echo messages (demonstrates local-exec)
- Random pet names for demonstration
- A local output file with configuration details

## Variables

- `environment` - Environment name (default: "demo")
- `message` - Message to display (default: "Hello from Slate Runner!")
- `instance_count` - Number of instances (default: 1)

## Usage with Slate Runner

### Option 1: Using the Web UI

1. Go to http://localhost:5000/jobs
2. Click "Create Job"
3. Fill in:
   - **Repository URL**: `https://github.com/YOUR_USERNAME/slate-runner-demo` (or your fork)
   - **Operation**: `plan` or `apply`
   - **Environment Variables** (optional):
   ```json
   {
     "TF_LOG": "INFO"
   }
   ```
   - **Terraform Variables** (optional):
   ```
   environment = "production"
   message = "Hello from my demo!"
   instance_count = 3
   ```

### Option 2: Using the API

```bash
curl -X POST http://localhost:5000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "runner-001",
    "repo_url": "https://github.com/YOUR_USERNAME/slate-runner-demo",
    "operation": "plan",
    "env_vars": {
      "TF_LOG": "INFO"
    },
    "tfvars": "environment = \"production\"\nmessage = \"Hello!\"\ninstance_count = 2"
  }'
```

## Expected Output

After running `terraform apply`, you should see:
- Console output with the echoed messages
- Generated random pet names
- A local `output.txt` file with configuration details
- Outputs showing environment, message, and server names

## Publishing This Repo

To use this as a demo:

1. Initialize git (if not already done):
   ```bash
   cd demo-terraform-repo
   git init
   git add .
   git commit -m "Initial commit"
   ```

2. Create a GitHub repository

3. Push:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME
   git push -u origin main
   ```

4. Use the repository URL in Slate Runner job creation
