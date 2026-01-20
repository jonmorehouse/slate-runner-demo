# Implementation Plan: State Sync & Enhanced UI

## Requirements Analysis

### 1. State Sync Job
**Problem:** Runner state is currently auto-synced. Want manual sync via job instead.
**Solution:** Add new "state_sync" operation type

### 2. Online/Offline Detection
**Status:** Already working via heartbeat mechanism
**Enhancement:** Add visual indicators and metrics

### 3. Graph View UI
**Problem:** Current list view doesn't show topology
**Solution:** Add network graph visualization

---

## Implementation Tasks

### Task 1: Add State Sync Job Type

#### 1.1 Add state_sync to operations
**File:** `control-plane/models.py`
```python
class JobOperation(Enum):
    """Terraform operation type."""
    PLAN = "plan"
    APPLY = "apply"
    REFRESH = "refresh"
    STATE_SYNC = "state_sync"  # NEW
```

#### 1.2 Create StateSyncTask
**File:** `runner/tasks/state_sync_task.py` (NEW)
```python
class StateSyncTask(BaseTerraformTask):
    """Sync runner state to control plane."""
    
    def get_type(self) -> str:
        return "state_sync"
    
    def execute(self, context: TaskContext) -> TaskResult:
        # Read runner state from S3
        # Upload to control plane via API
        # Return stats
```

#### 1.3 Register state_sync task
**File:** `runner/loops.py`
Add to `_register_tasks()`:
```python
self.task_registry.register(StateSyncTask())
```

#### 1.4 Add state upload endpoint
**File:** `control-plane/app.py`
```python
@app.route('/api/agents/<agent_id>/state', methods=['POST'])
def upload_runner_state(agent_id):
    """Receive runner state from sync job."""
```

---

### Task 2: Enhance Online/Offline Detection

#### 2.1 Add connection metrics
**File:** `control-plane/models.py`
```python
@dataclass
class Agent:
    # ... existing fields ...
    connected_at: Optional[str] = None
    disconnected_at: Optional[str] = None
    connection_count: int = 0
```

#### 2.2 Track connection history
**File:** `control-plane/app.py`
Update health check endpoint to track:
- First connection time
- Last disconnection time  
- Total reconnections

#### 2.3 Add visual indicators
**File:** `control-plane/templates/partials/agent_list.html`
- Pulsing dot for online
- Gray dot for offline
- Time since last heartbeat
- Connection duration

---

### Task 3: Network Graph View

#### 3.1 Add D3.js for visualization
**File:** `control-plane/templates/base.html`
```html
<script src="https://d3js.org/d3.v7.min.js"></script>
```

#### 3.2 Create graph view template
**File:** `control-plane/templates/graph_view.html` (NEW)
```html
<div id="runner-graph"></div>
<script>
  // D3 force-directed graph
  // Nodes: runners
  // Colors: online/offline/locked
  // Size: based on jobs completed
</script>
```

#### 3.3 Add graph endpoint
**File:** `control-plane/app.py`
```python
@app.route('/graph')
def graph_view():
    """Network graph of runners."""
    agents = meta_storage.list_agents()
    return render_template('graph_view.html', agents=agents)
```

#### 3.4 Add view toggle
**File:** `control-plane/templates/dashboard.html`
```html
<div class="view-toggle">
  <button>List View</button>
  <button>Graph View</button>
</div>
```

---

## Detailed Implementation

### State Sync Flow

```
Control Plane → Creates "state_sync" job
     ↓
Runner → Claims job
     ↓
Runner → Reads state from S3
     ↓
Runner → POST /api/agents/<id>/state
     ↓
Control Plane → Stores state snapshot
     ↓
Runner → Marks job complete
```

### Graph View Features

**Node Properties:**
- Color: Green (online/unlocked), Yellow (online/locked), Red (offline), Blue (adopted/pending)
- Size: Based on jobs_completed count
- Label: Runner name + ID
- Border: Thick if locked

**Interactions:**
- Click node → Navigate to agent detail
- Hover → Show tooltip (stats, last heartbeat)
- Drag → Reposition nodes
- Zoom/Pan → Navigate large fleets

**Layout:**
- Force-directed graph
- Runners cluster by status
- Connection lines show job flow (optional)

---

## Files to Create

1. `runner/tasks/state_sync_task.py` - State sync task
2. `control-plane/templates/graph_view.html` - Network visualization
3. `control-plane/static/css/graph.css` - Graph styles
4. `control-plane/static/js/graph.js` - Graph logic

## Files to Modify

1. `control-plane/models.py` - Add STATE_SYNC operation, connection fields
2. `control-plane/app.py` - Add state upload endpoint, graph view
3. `runner/loops.py` - Register state_sync task
4. `control-plane/templates/base.html` - Add D3.js
5. `control-plane/templates/dashboard.html` - Add view toggle
6. `control-plane/templates/partials/agent_list.html` - Enhanced status

---

## Testing Plan

### State Sync
```bash
# Create state sync job
curl -X POST http://localhost:5000/api/jobs \
  -d '{"agent_id": "runner-001", "operation": "state_sync"}'

# Verify state uploaded
curl http://localhost:5000/api/agents/runner-001/state
```

### Graph View
```bash
# Navigate to graph
open http://localhost:5000/graph

# Verify:
- [ ] All runners shown
- [ ] Colors correct (online/offline/locked)
- [ ] Click navigation works
- [ ] Real-time updates
```

### Online/Offline
```bash
# Stop runner
# Wait 15 seconds
# Verify UI shows offline

# Restart runner
# Verify UI shows online + connection count++
```

---

## Priority

**High Priority:**
1. State sync job type ← Core functionality
2. Enhanced online/offline indicators ← User experience

**Medium Priority:**
3. Graph view visualization ← Nice to have, impressive for demo

**Timeline:**
- State sync: ~1 hour
- Enhanced status: ~30 min
- Graph view: ~2 hours

Would you like me to implement these?
