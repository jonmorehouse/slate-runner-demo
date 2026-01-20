"""Main Flask application for the control plane."""
import os
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv

from models import Agent, Job, HealthCheck, Command, JobStatus, AgentStatus
from storage import MetaStorage, RunnerStorage
from validation import validate_required_fields, validate_job_status, validate_repo_url, validate_operation

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
CORS(app)

# Initialize storage
meta_storage = MetaStorage()
runner_storage = RunnerStorage()


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(400)
def bad_request(e):
    """Handle bad request errors."""
    return jsonify({
        'error': 'Bad Request',
        'message': str(e.description) if hasattr(e, 'description') else str(e),
        'status': 400
    }), 400


@app.errorhandler(404)
def not_found(e):
    """Handle not found errors."""
    return jsonify({
        'error': 'Not Found',
        'message': str(e.description) if hasattr(e, 'description') else 'Resource not found',
        'status': 404
    }), 404


@app.errorhandler(409)
def conflict(e):
    """Handle conflict errors."""
    return jsonify({
        'error': 'Conflict',
        'message': str(e.description) if hasattr(e, 'description') else str(e),
        'status': 409
    }), 409


@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors."""
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred',
        'status': 500
    }), 500



# ============================================================================
# Web UI Routes (HTMX)
# ============================================================================

@app.route('/')
def index():
    """Dashboard showing all agents."""
    agents = meta_storage.list_agents()
    
    # Update agent status based on heartbeat
    for agent_data in agents:
        agent = Agent.from_dict(agent_data)
        was_online = agent.status == AgentStatus.ONLINE.value
        
        if agent.is_online():
            agent.status = AgentStatus.ONLINE.value
        else:
            agent.status = AgentStatus.OFFLINE.value
            # Track disconnection time if transitioning from online to offline
            if was_online:
                agent.disconnected_at = datetime.utcnow().isoformat()
        
        meta_storage.save_agent(agent.to_dict())
    
    return render_template('dashboard.html', agents=agents)


@app.route('/agents/<agent_id>')
def agent_detail(agent_id):
    """Agent detail page."""
    agent_data = meta_storage.get_agent(agent_id)
    if not agent_data:
        return "Agent not found", 404
    
    agent = Agent.from_dict(agent_data)
    jobs = meta_storage.list_jobs(agent_id=agent_id)
    
    return render_template('agent_detail.html', agent=agent, jobs=jobs)


@app.route('/graph')
def graph_view():
    """Graph view of runners."""
    agents = meta_storage.list_agents()
    
    # Update agent status
    for agent_data in agents:
        agent = Agent.from_dict(agent_data)
        was_online = agent.status == AgentStatus.ONLINE.value
        
        if agent.is_online():
            agent.status = AgentStatus.ONLINE.value
        else:
            agent.status = AgentStatus.OFFLINE.value
            if was_online:
                agent.disconnected_at = datetime.utcnow().isoformat()
        
        meta_storage.save_agent(agent.to_dict())
    
    return render_template('graph.html', agents=agents)


@app.route('/jobs')
def jobs_page():
    """Jobs list page."""
    jobs = meta_storage.list_jobs()
    agents = meta_storage.list_agents()
    return render_template('jobs.html', jobs=jobs, agents=agents)


@app.route('/jobs/<job_id>')
def job_detail(job_id):
    """Job detail page."""
    job_data = meta_storage.get_job(job_id)
    if not job_data:
        return "Job not found", 404
    
    job = Job.from_dict(job_data)
    
    # Get output if available
    if job.state_path:
        output = runner_storage.get_output(job_id)
        if output:
            job.output = output
    
    return render_template('job_detail.html', job=job)


# ============================================================================
# HTMX Partial Routes
# ============================================================================

@app.route('/partials/agents')
def agents_partial():
    """Partial for agent list (for polling)."""
    agents = meta_storage.list_agents()
    
    # Update status
    for agent_data in agents:
        agent = Agent.from_dict(agent_data)
        was_online = agent.status == AgentStatus.ONLINE.value
        
        if agent.is_online():
            agent.status = AgentStatus.ONLINE.value
        else:
            agent.status = AgentStatus.OFFLINE.value
            # Track disconnection time if transitioning from online to offline
            if was_online:
                agent.disconnected_at = datetime.utcnow().isoformat()
        
        meta_storage.save_agent(agent.to_dict())
    
    return render_template('partials/agent_list.html', agents=agents)


@app.route('/partials/jobs')
def jobs_partial():
    """Partial for job list (for polling)."""
    jobs = meta_storage.list_jobs()
    return render_template('partials/job_list.html', jobs=jobs)


# ============================================================================
# Agent API
# ============================================================================

@app.route('/api/agents', methods=['POST'])
def register_agent():
    """Register a new agent."""
    data = request.json
    
    valid, error = validate_required_fields(data, ['agent_id'])
    if not valid:
        return jsonify({'error': error}), 400
    
    agent_id = data.get('agent_id')
    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400
    
    # Check if agent already exists
    existing = meta_storage.get_agent(agent_id)
    if existing:
        # Update existing agent
        agent = Agent.from_dict(existing)
        
        # Track reconnection if it was offline
        was_offline = agent.status == AgentStatus.OFFLINE.value
        if was_offline:
            agent.connected_at = datetime.utcnow().isoformat()
            agent.connection_count = agent.connection_count + 1
        
        agent.last_heartbeat = datetime.utcnow().isoformat()
        agent.status = AgentStatus.ONLINE.value
        agent.name = data.get('name', agent.name)
        if data.get('metadata'):
            agent.metadata = data['metadata']
    else:
        # Create new agent
        agent = Agent(
            agent_id=agent_id,
            name=data.get('name', agent_id),
            status=AgentStatus.ONLINE.value,
            last_heartbeat=datetime.utcnow().isoformat(),
            metadata=data.get('metadata'),
            created_at=datetime.utcnow().isoformat(),
            connected_at=datetime.utcnow().isoformat(),
            connection_count=1
        )
    
    meta_storage.save_agent(agent.to_dict())
    return jsonify(agent.to_dict()), 201


@app.route('/api/agents', methods=['GET'])
def list_agents():
    """List all agents."""
    agents = meta_storage.list_agents()
    return jsonify(agents)


@app.route('/api/agents/<agent_id>', methods=['GET'])
def get_agent(agent_id):
    """Get a specific agent."""
    agent_data = meta_storage.get_agent(agent_id)
    if not agent_data:
        return jsonify({'error': 'Agent not found'}), 404
    return jsonify(agent_data)


@app.route('/api/agents/<agent_id>', methods=['DELETE'])
def delete_agent(agent_id):
    """Delete an agent."""
    meta_storage.delete_agent(agent_id)
    return '', 204


@app.route('/api/agents/<agent_id>/adopt', methods=['POST'])
def adopt_agent(agent_id):
    """Adopt a runner agent."""
    agent_data = meta_storage.get_agent(agent_id)
    if not agent_data:
        return jsonify({'error': 'Agent not found'}), 404
    
    agent = Agent.from_dict(agent_data)
    
    if agent.adopted:
        return jsonify({'error': 'Agent already adopted'}), 409
    
    # Mark as adopted
    agent.adopted = True
    agent.adopted_at = datetime.now(timezone.utc).isoformat()
    
    # Optional: track who adopted
    data = request.json or {}
    if 'adopted_by' in data:
        agent.adopted_by = data['adopted_by']
    
    meta_storage.save_agent(agent.to_dict())
    
    return jsonify(agent.to_dict()), 200


@app.route('/api/agents/<agent_id>/unadopt', methods=['POST'])
def unadopt_agent(agent_id):
    """Unadopt a runner agent (for testing/management)."""
    agent_data = meta_storage.get_agent(agent_id)
    if not agent_data:
        return jsonify({'error': 'Agent not found'}), 404
    
    agent = Agent.from_dict(agent_data)
    agent.adopted = False
    agent.adopted_at = None
    agent.adopted_by = None
    
    meta_storage.save_agent(agent.to_dict())
    
    return jsonify(agent.to_dict()), 200


@app.route('/api/agents/<agent_id>/lock', methods=['POST'])
def lock_agent(agent_id):
    """Lock or unlock a runner agent."""
    agent_data = meta_storage.get_agent(agent_id)
    if not agent_data:
        return jsonify({'error': 'Agent not found'}), 404
    
    data = request.json or {}
    lock_state = data.get('locked', True)  # Default to locking
    
    agent = Agent.from_dict(agent_data)
    agent.locked = lock_state
    
    meta_storage.save_agent(agent.to_dict())
    
    return jsonify(agent.to_dict()), 200


@app.route('/api/agents/<agent_id>/state', methods=['POST'])
def upload_agent_state(agent_id):
    """Receive and store runner state from a state sync job."""
    agent_data = meta_storage.get_agent(agent_id)
    if not agent_data:
        return jsonify({'error': 'Agent not found'}), 404
    
    data = request.json
    
    valid, error = validate_required_fields(data, ['state'])
    if not valid:
        return jsonify({'error': error}), 400
    
    agent = Agent.from_dict(agent_data)
    agent.runner_state = data['state']
    
    # Parse Terraform states if provided
    terraform_states = data.get('terraform_states', [])
    resources = []
    
    for tf_state_entry in terraform_states:
        job_id = tf_state_entry.get('job_id', 'unknown')
        tf_state = tf_state_entry.get('state', {})
        
        # Extract resources from Terraform state
        # Terraform state v4 format: state.resources[]
        state_resources = tf_state.get('resources', [])
        
        for resource in state_resources:
            resource_type = resource.get('type', 'unknown')
            resource_name = resource.get('name', 'unknown')
            resource_mode = resource.get('mode', 'managed')
            
            # Get instances (can be multiple for count/for_each)
            instances = resource.get('instances', [])
            
            for idx, instance in enumerate(instances):
                attributes = instance.get('attributes', {})
                
                # Extract common attributes
                resource_id = attributes.get('id', 'unknown')
                
                resources.append({
                    'job_id': job_id,
                    'type': resource_type,
                    'name': resource_name,
                    'mode': resource_mode,
                    'id': resource_id,
                    'index': idx if len(instances) > 1 else None,
                    'attributes': attributes
                })
    
    agent.terraform_resources = resources
    agent.last_state_sync = datetime.utcnow().isoformat()
    
    meta_storage.save_agent(agent.to_dict())
    
    return jsonify({
        'status': 'ok',
        'message': 'State uploaded successfully',
        'resources_count': len(resources),
        'synced_at': agent.last_state_sync
    }), 200


# ============================================================================
# Health Check API
# ============================================================================

@app.route('/api/health', methods=['POST'])
def submit_health_check():
    """Submit a health check from an agent."""
    data = request.json
    
    valid, error = validate_required_fields(data, ['agent_id'])
    if not valid:
        return jsonify({'error': error}), 400
    
    agent_id = data.get('agent_id')
    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400
    
    # Update agent's last heartbeat
    agent_data = meta_storage.get_agent(agent_id)
    if agent_data:
        agent = Agent.from_dict(agent_data)
        agent.last_heartbeat = datetime.utcnow().isoformat()
        agent.status = AgentStatus.ONLINE.value
        meta_storage.save_agent(agent.to_dict())
    
    # Save health check
    health_check = HealthCheck(
        agent_id=agent_id,
        timestamp=datetime.utcnow().isoformat(),
        cpu_percent=data.get('cpu_percent'),
        memory_percent=data.get('memory_percent'),
        disk_percent=data.get('disk_percent'),
        metadata=data.get('metadata')
    )
    
    meta_storage.save_health_check(health_check.to_dict())
    return jsonify({'status': 'ok'}), 200


# ============================================================================
# Job API
# ============================================================================

@app.route('/api/jobs', methods=['POST'])
def create_job():
    """Create a new job."""
    try:
        data = request.json
        
        # Debug logging
        print(f"[API] POST /api/jobs - Content-Type: {request.content_type}")
        print(f"[API] Request data: {data}")
        
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400
        
        valid, error = validate_required_fields(data, ['agent_id', 'repo_url'])
        if not valid:
            print(f"[API] Validation error: {error}")
            return jsonify({'error': error}), 400
        
        if not validate_repo_url(data['repo_url']):
            return jsonify({'error': 'Invalid repository URL'}), 400
        
        operation = data.get('operation', 'plan')
        if not validate_operation(operation):
            return jsonify({'error': 'Invalid operation type'}), 400
        
        agent_id = data.get('agent_id')
        repo_url = data.get('repo_url')
        
        # Verify agent exists
        agent_data = meta_storage.get_agent(agent_id)
        if not agent_data:
            return jsonify({'error': 'Agent not found'}), 404
        
        # Handle optional fields - normalize empty to None
        env_vars = data.get('env_vars') or None
        tfvars = data.get('tfvars') or None
        tf_version = data.get('tf_version') or None
        working_dir = data.get('working_dir') or None
        
        job = Job(
            job_id=str(uuid.uuid4()),
            agent_id=agent_id,
            repo_url=repo_url,
            operation=operation,
            status=JobStatus.QUEUED.value,
            env_vars=env_vars,
            tfvars=tfvars,
            tf_version=tf_version,
            working_dir=working_dir,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        print(f"[API] Created job {job.job_id} for agent {agent_id}")
        meta_storage.save_job(job.to_dict())
        return jsonify(job.to_dict()), 201
        
    except Exception as e:
        print(f"[API] Error creating job: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """List all jobs."""
    agent_id = request.args.get('agent_id')
    jobs = meta_storage.list_jobs(agent_id=agent_id)
    return jsonify(jobs)


@app.route('/api/jobs/pending', methods=['GET'])
def get_pending_jobs():
    """Get pending jobs for an agent."""
    agent_id = request.args.get('agent_id')
    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400
    
    jobs = meta_storage.list_jobs(agent_id=agent_id)
    pending = [j for j in jobs if j['status'] == JobStatus.QUEUED.value]
    
    # Return only the first pending job
    if pending:
        return jsonify(pending[0])
    else:
        return jsonify(None)


@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job(job_id):
    """Get a specific job."""
    job_data = meta_storage.get_job(job_id)
    if not job_data:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job_data)




@app.route('/api/jobs/<job_id>/claim', methods=['POST'])
def claim_job(job_id):
    """Atomically claim a pending job."""
    data = request.json
    
    # Validate request
    valid, error = validate_required_fields(data, ['agent_id'])
    if not valid:
        return jsonify({'error': error}), 400
    
    agent_id = data.get('agent_id')
    
    # Verify agent exists
    agent_data = meta_storage.get_agent(agent_id)
    if not agent_data:
        return jsonify({'error': 'Agent not found'}), 404
    
    # Attempt to claim the job
    success, error_msg = meta_storage.claim_job(job_id, agent_id)
    
    if not success:
        if error_msg == "Job not found":
            return jsonify({'error': error_msg}), 404
        else:
            return jsonify({'error': error_msg}), 409
    
    # Return claimed job
    job_data = meta_storage.get_job(job_id)
    return jsonify(job_data), 200


@app.route('/api/jobs/<job_id>', methods=['PATCH'])
def update_job(job_id):
    """Update a job's status."""
    data = request.json
    
    if 'status' in data and not validate_job_status(data['status']):
        return jsonify({'error': 'Invalid job status'}), 400
    
    job_data = meta_storage.get_job(job_id)
    if not job_data:
        return jsonify({'error': 'Job not found'}), 404
    
    data = request.json
    job = Job.from_dict(job_data)
    
    # Update fields
    if 'status' in data:
        job.status = data['status']
        if data['status'] == JobStatus.IN_PROGRESS.value and not job.started_at:
            job.started_at = datetime.now(timezone.utc).isoformat()
        elif data['status'] in [JobStatus.SUCCESSFUL.value, JobStatus.FAILED.value]:
            job.completed_at = datetime.now(timezone.utc).isoformat()
    
    if 'output' in data:
        job.output = data['output']
    if 'error' in data:
        job.error = data['error']
    if 'state_path' in data:
        job.state_path = data['state_path']
    
    meta_storage.save_job(job.to_dict())
    return jsonify(job.to_dict())


# ============================================================================
# Command API
# ============================================================================

@app.route('/api/agents/<agent_id>/commands', methods=['GET'])
def get_agent_commands(agent_id):
    """Get pending commands for an agent."""
    commands = meta_storage.list_pending_commands(agent_id)
    return jsonify(commands)


@app.route('/api/agents/<agent_id>/commands', methods=['POST'])
def send_agent_command(agent_id):
    """Send a command to an agent."""
    data = request.json
    
    command_type = data.get('command_type')
    if not command_type:
        return jsonify({'error': 'command_type is required'}), 400
    
    command = Command(
        command_id=str(uuid.uuid4()),
        agent_id=agent_id,
        command_type=command_type,
        params=data.get('params'),
        created_at=datetime.utcnow().isoformat()
    )
    
    meta_storage.save_command(command.to_dict())
    return jsonify(command.to_dict()), 201


@app.route('/api/commands/<command_id>', methods=['PATCH'])
def update_command(command_id):
    """Mark a command as executed."""
    command_data = meta_storage.get_command(command_id)
    if not command_data:
        return jsonify({'error': 'Command not found'}), 404
    
    data = request.json
    command = Command.from_dict(command_data)
    
    if 'executed' in data:
        command.executed = data['executed']
        command.executed_at = datetime.utcnow().isoformat()
    
    meta_storage.save_command(command.to_dict())
    return jsonify(command.to_dict())


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5005))
    app.run(host='0.0.0.0', port=port, debug=True)