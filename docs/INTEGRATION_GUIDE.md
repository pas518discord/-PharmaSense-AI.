# PharmaSense AI — Complete Integration Guide

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PHARMASENSE AI ECOSYSTEM                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SIMULATION LAYER (pharma_sense_ai.py)                         │
│  ├─ PharmaFreezer (-20°C to -80°C)                            │
│  ├─ DrugDispenser (15-25°C)                                   │
│  └─ BloodStorage (1-6°C)                                       │
│      All with deterministic physics & 15 failure profiles      │
│                                                                 │
│  PREDICTION LAYER (predict_failure)                            │
│  ├─ Temperature rise rates                                     │
│  ├─ Inventory depletion                                        │
│  ├─ Access anomalies                                           │
│  └─ Returns: {predicted_failure, confidence, time_to_critical} │
│                                                                 │
│  DECISION LAYER (offline_decisions.py + triage)               │
│  ├─ decide_freezer() → 4 CRITICAL pathways                    │
│  ├─ decide_dispenser() → 2 CRITICAL pathways                  │
│  ├─ decide_blood_storage() → 3 CRITICAL pathways              │
│  ├─ decide_fleet() → Multi-site cascade detection             │
│  └─ triage() → Router to appropriate decision function        │
│                                                                 │
│  ORCHESTRATION LAYER (gemini_orchestrator.py)                 │
│  ├─ Queries SplunkMCP for telemetry                           │
│  ├─ Sends enriched context to Gemini API                      │
│  ├─ Falls back to decision trees (offline capability)         │
│  ├─ Posts HITL alerts to Slack webhook                        │
│  └─ Logs decisions for audit trail                            │
│                                                                 │
│  ALERTING LAYER (Slack Webhook)                               │
│  ├─ RED alerts for CRITICAL decisions                         │
│  ├─ ORANGE alerts for HIGH decisions                          │
│  ├─ Approve/Override buttons                                   │
│  └─ Rich formatting with analysis & metadata                  │
│                                                                 │
│  LOGGING LAYER (Audit Trail)                                   │
│  ├─ Decision history                                           │
│  ├─ Equipment state tracking                                   │
│  └─ Compliance records                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Component Overview

### 1. Core Simulation Engine (pharma_sense_ai.py)

**Purpose**: Provide deterministic pharmaceutical equipment simulation

**3 Equipment Classes**:
- `PharmaFreezer`: Ultra-low temperature storage
  - Temperature range: -20°C to -80°C
  - Failure modes: compressor_failure, door_seal_breach, power_failure, sensor_drift
  - Physics: 0.8°C/hr rise (compressor), 2°C/hr (power), humidity accumulation

- `DrugDispenser`: Automated drug distribution
  - Temperature range: 15-25°C
  - Failure modes: access_anomaly, motor_jam, inventory_low, temp_out_of_range
  - Physics: inventory depletion, access pattern tracking, accuracy degradation

- `BloodStorage`: Blood bank refrigeration
  - Temperature range: 1-6°C
  - Failure modes: temp_excursion, unit_expiry, contamination_risk, seal_breach
  - Physics: CO2 accumulation, bacterial risk, 42-day shelf life

**Usage**:
```python
from pharma_sense_ai import mock_db, predict_failure

# Initialize fleet
db = mock_db()  # 11 equipment units across 3 sites

# Simulate time
for _ in range(20):
    db['pharma_freezers'][0].step(0.5)  # 0.5 hour increments

# Get predictions
snapshot = db['pharma_freezers'][0].snapshot(datetime.now())
prediction = predict_failure(snapshot)
print(prediction['predicted_failure'])      # "COMPRESSOR_FAILURE"
print(prediction['confidence'])              # 0.95
print(prediction['time_to_critical_hours'])  # 42.5
```

### 2. Decision Trees (pharma_sense_ai.py + offline_decisions.py)

**Purpose**: Generate WHO-compliant action plans without cloud API

**4 Decision Functions**:
- `decide_freezer(data)` - Temperature, compressor, power, sensor management
- `decide_dispenser(data)` - Access control, inventory, motor status
- `decide_blood_storage(data)` - Temperature safety, contamination, shelf life
- `decide_fleet(site_metrics)` - Multi-site cascade detection

**Dispatcher**:
- `triage(equipment_snapshot)` - Routes to correct decision function

**Decision Schema**:
```python
{
    "decision_id": "DEC-2026-FREEZER-FZ-01",
    "analysis": "Detailed human-readable analysis",
    "severity": 0.96,  # 0.0-1.0
    "risk_level": "CRITICAL|HIGH|MEDIUM|LOW",
    "recoverable": True/False,
    "requires_human_approval": True/False,
    "approval_message": "Action message if human approval needed",
    "action_plan": [
        {
            "channel": "SAFETY|MAINTENANCE|COMPLIANCE|NOTIFICATION",
            "action": "ACTION_NAME",
            "params": { "key": "value" }
        }
    ]
}
```

**Usage**:
```python
from pharma_sense_ai import triage

snapshot = equipment.snapshot(datetime.now())
decision = triage(snapshot)

if decision['risk_level'] == 'CRITICAL':
    send_approval_alert(decision)
```

### 3. Gemini Orchestrator (gemini_orchestrator.py)

**Purpose**: Cloud-connected orchestration with automatic offline fallback

**Main Method**:
```python
orchestrator = GeminiOrchestrator(".env")
decision = orchestrator.run_triage_loop(
    query_type="operational",  # operational|predictive|compliance
    appliance_id="FZ-01"
)
```

**Flow**:
1. Query Splunk MCP (or mock_db) for telemetry
2. Build Gemini system instruction + prompt
3. Query Gemini API with temperature=0.1
4. Parse JSON response (or fallback to `offline_triage()`)
5. If `requires_human_approval`: send Slack alert
6. Log decision to audit trail
7. Return decision

**Three Triage Modes**:

| Mode | Purpose | Use Case | Expected Risk |
|------|---------|----------|----------------|
| `operational` | Real-time failure detection | Compressor fail, power loss | CRITICAL/HIGH |
| `predictive` | Trend analysis & forecasting | Sensor drift, temperature trending | HIGH/MEDIUM |
| `compliance` | Regulatory & access control | Access anomalies, DEA compliance | CRITICAL/MEDIUM |

### 4. Slack Integration

**HITL Alert Format**:
```
🚨 PharmaSense Alert — FZ-01
Risk Level:     CRITICAL
Severity:       96%
Equipment:      PharmaFreezer
Status:         COMPRESSOR_FAIL
Analysis:       Compressor failure detected. Temp rising 0.8°C/hr...
[Approve Action]  [Override — Keep Running]
```

**Colors**:
- **RED** (#d62728): CRITICAL decisions
- **ORANGE** (#ff7f0e): HIGH decisions
- **No Alert**: MEDIUM, LOW decisions

**Buttons**:
- "Approve Action" → Click to authorize
- "Override — Keep Running" → Click to skip

### 5. Audit Trail & Logging

**Decision History**:
```python
orchestrator.call_history
# Returns:
# [
#   {
#     "timestamp": "2026-06-15T18:10:42.123456",
#     "decision_id": "DEC-2026-FREEZER-FZ-01",
#     "appliance_id": "FZ-01",
#     "query_type": "operational",
#     "risk_level": "CRITICAL",
#     "requires_approval": True,
#     "action_count": 4
#   }
# ]
```

## Integration Workflows

### Workflow 1: Real-Time Monitoring Loop

```python
from gemini_orchestrator import GeminiOrchestrator
from datetime import datetime
import time

orchestrator = GeminiOrchestrator(".env")

while True:
    # Query each appliance
    for appliance_id in ["FZ-01", "FZ-04", "DD-01", "BS-01"]:
        decision = orchestrator.run_triage_loop(
            query_type="operational",
            appliance_id=appliance_id
        )
        
        # Handle critical decisions
        if decision['requires_human_approval']:
            print(f"ALERT: {appliance_id} requires approval")
            # User reviews in Slack and clicks button
        
        # Execute approved actions
        for action in decision['action_plan']:
            execute_action(action)
    
    # Wait before next cycle
    time.sleep(300)  # 5 minutes
```

### Workflow 2: Batch Triage (All Sites)

```python
from gemini_orchestrator import GeminiOrchestrator

orchestrator = GeminiOrchestrator(".env")

# Triage all equipment across all sites
for site_id in ["site_a", "site_b", "site_c"]:
    decision = orchestrator.run_triage_loop(
        query_type="compliance",
        site_id=site_id
    )
    
    # Generate compliance report
    report = generate_compliance_report(
        site_id=site_id,
        decision=decision,
        timestamp=datetime.now()
    )
    submit_to_regulatory_database(report)
```

### Workflow 3: Predictive Maintenance

```python
from gemini_orchestrator import GeminiOrchestrator
from datetime import datetime, timedelta

orchestrator = GeminiOrchestrator(".env")

# Run predictive analysis
predictions = []
for equipment in fleet:
    decision = orchestrator.run_triage_loop(
        query_type="predictive",
        appliance_id=equipment.id
    )
    
    predictions.append({
        "equipment_id": equipment.id,
        "risk_level": decision['risk_level'],
        "analysis": decision['analysis']
    })

# Sort by risk and schedule maintenance
predictions.sort(key=lambda x: x['risk_level'])
for pred in predictions[:5]:  # Top 5 riskiest
    schedule_maintenance(
        equipment_id=pred['equipment_id'],
        priority="HIGH",
        reason=pred['analysis']
    )
```

### Workflow 4: Offline Operation (No Gemini API)

```python
# When Gemini API unavailable or not configured
orchestrator = GeminiOrchestrator(".env")  # No GEMINI_API_KEY in .env

decision = orchestrator.run_triage_loop(
    query_type="operational",
    appliance_id="FZ-01"
)
# Automatically uses offline_triage() - same decision schema
# No code changes needed!
```

## Configuration

### 1. Environment Setup

**Create .env file**:
```bash
cp .env.template .env
```

**Edit .env with credentials**:
```
GEMINI_API_KEY=AIzaSyD...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T.../B.../X...
SPLUNK_MCP_URL=http://localhost:5000
```

### 2. API Key Acquisition

**Gemini API**:
1. Go to https://ai.google.dev/
2. Click "Get API key"
3. Create new API key
4. Add to .env: `GEMINI_API_KEY=<your_key>`

**Slack Webhook**:
1. Go to https://api.slack.com/messaging/webhooks
2. Create new webhook for PharmaSense channel
3. Copy webhook URL
4. Add to .env: `SLACK_WEBHOOK_URL=<your_url>`

### 3. Python Dependencies

**No external dependencies!**
```python
# Only stdlib required:
import json          # JSON serialization
import urllib        # HTTP requests (no requests library)
import datetime      # Timestamp handling
```

**To use offline mode**:
```bash
python gemini_orchestrator.py  # Works without any API keys!
```

## Usage Examples

### Example 1: Single Equipment Triage

```python
from gemini_orchestrator import GeminiOrchestrator

orchestrator = GeminiOrchestrator()
decision = orchestrator.run_triage_loop(appliance_id="FZ-01")

print(f"Risk: {decision['risk_level']}")
print(f"Actions: {len(decision['action_plan'])}")
for action in decision['action_plan']:
    print(f"  - [{action['channel']}] {action['action']}")
```

### Example 2: Site-Wide Triage

```python
orchestrator = GeminiOrchestrator()
decision = orchestrator.run_triage_loop(site_id="site_a")

if decision['requires_human_approval']:
    print("Alerting team via Slack...")
    # Slack message automatically sent by send_hitl_alert()
```

### Example 3: Triage History

```python
orchestrator = GeminiOrchestrator()

# Run multiple triages
for appliance_id in ["FZ-01", "FZ-04", "DD-01"]:
    orchestrator.run_triage_loop(appliance_id=appliance_id)

# Review history
for entry in orchestrator.call_history:
    print(f"{entry['appliance_id']}: {entry['risk_level']} "
          f"({entry['timestamp']})")
```

### Example 4: Predictive Analysis

```python
orchestrator = GeminiOrchestrator()

# Analyze equipment degradation trend
decision = orchestrator.run_triage_loop(
    query_type="predictive",
    appliance_id="FZ-04"
)

if decision['analysis']:
    print(f"Trend: {decision['analysis']}")
    # Take preventive action before critical failure
```

## Testing

### Test 1: Unit Tests (Physics Validation)

```bash
python test_pharma_sense.py
```

Output: 30+ physics tests validating:
- Temperature rise rates
- Inventory depletion
- Status state machines
- Failure predictions

### Test 2: Integration Test

```bash
python integration_test.py
```

Output: Complete system validation including:
- Telemetry collection
- Decision generation
- Approval workflows
- Action planning

### Test 3: Orchestrator Demo

```bash
python gemini_orchestrator.py
```

Output: Three scenarios:
1. Operational: Compressor failure
2. Predictive: Power failure trend
3. Compliance: Access anomaly

## Troubleshooting

### Issue: "No Gemini API key - using offline fallback"

**Cause**: GEMINI_API_KEY not configured  
**Solution**: Either:
- Get API key from https://ai.google.dev/ and add to .env
- OR keep using offline (fully autonomous mode)

### Issue: Slack alerts not sending

**Cause**: SLACK_WEBHOOK_URL not configured  
**Solution**:
- Get webhook from https://api.slack.com/messaging/webhooks
- Add to .env: `SLACK_WEBHOOK_URL=https://hooks.slack.com/...`

### Issue: Gemini API returns non-JSON

**Cause**: API quota exceeded, network error, or schema mismatch  
**Solution**:
- Check API status: https://ai.google.dev/
- Verify quota at https://aistudio.google.com/
- System automatically falls back to offline trees
- Check error logs

### Issue: All decisions return LOW risk

**Cause**: Equipment in nominal state  
**Solution**:
- Run with equipment in failure profile: `FZ-01` (compressor failure)
- Simulate longer time period: Run integration_test.py first
- Check fleet state: `python -c "from pharma_sense_ai import mock_db; db=mock_db(); print(db['pharma_freezers'][0].profile)"`

## Performance Metrics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Equipment step (physics) | <1ms | Per equipment per timestep |
| Snapshot generation | <5ms | Per equipment |
| Offline decision tree | <10ms | Pure local computation |
| Gemini API query | 2-5s | Includes network latency |
| Slack webhook POST | ~1s | Webhook delivery |
| Full triage loop (online) | 3-6s | Gemini + alerts + logging |
| Full triage loop (offline) | <100ms | No API call |

## Security Best Practices

1. **Never hardcode API keys**
```python
# BAD
api_key = "AIzaSyD..."

# GOOD
from os import getenv
api_key = getenv("GEMINI_API_KEY")
```

2. **Protect .env file**
```bash
# Add to .gitignore
echo ".env" >> .gitignore

# Restrict file permissions (Linux/Mac)
chmod 600 .env
```

3. **Use environment variables in production**
```bash
# Set via CI/CD or deployment platform
export GEMINI_API_KEY=<secret>
export SLACK_WEBHOOK_URL=<secret>
```

4. **Rotate credentials regularly**
- Gemini API keys: Regenerate quarterly
- Slack webhooks: Rotate on team changes
- Access logs: Archive for compliance

## Advanced Integration

### Integration with Splunk HEC (Future)

```python
# Proposed: Log decisions to Splunk
from splunk_hec import HECClient

hec = HECClient(
    url=os.getenv("SPLUNK_HEC_URL"),
    token=os.getenv("SPLUNK_HEC_TOKEN")
)

hec.post_event({
    "decision_id": decision['decision_id'],
    "risk_level": decision['risk_level'],
    "sourcetype": "pharmasense:decision"
})
```

### Integration with Splunk Stream (Future)

```spl
# SPL search for monitoring
index=main sourcetype=pharmasense:decision risk_level=CRITICAL 
| stats count by appliance_id 
| alert
```

### Custom Action Handlers

```python
def execute_action(action):
    """Route actions to appropriate handler."""
    channel = action['channel']
    
    if channel == "SAFETY":
        handle_safety_action(action)
    elif channel == "MAINTENANCE":
        handle_maintenance_action(action)
    elif channel == "COMPLIANCE":
        handle_compliance_action(action)
    elif channel == "NOTIFICATION":
        handle_notification_action(action)
```

## Deployment Checklist

- [x] Python 3.7+ installed
- [x] pharma_sense_ai.py downloaded
- [x] gemini_orchestrator.py downloaded
- [x] .env file created with API keys (or empty for offline mode)
- [x] Gemini API enabled (if using cloud)
- [x] Slack webhook created (if using HITL)
- [x] Test connection: `python gemini_orchestrator.py`
- [x] Review audit trail format
- [x] Set up monitoring/logging pipeline
- [x] Document runbook for CRITICAL alerts

## Support

- **Offline**: System always works, even without API keys
- **Documentation**: GEMINI_ORCHESTRATOR.md has detailed API reference
- **Examples**: gemini_orchestrator.py includes three demo scenarios
- **Testing**: integration_test.py validates end-to-end functionality

---

**Version**: 1.0  
**Status**: Production Ready  
**License**: Apache 2.0
