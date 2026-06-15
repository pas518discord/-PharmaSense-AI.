# PharmaSense AI — Gemini Orchestrator

## Overview

The `GeminiOrchestrator` class provides cloud-connected decision orchestration for pharmaceutical equipment management. It integrates with Google's Gemini 1.5 Flash API while maintaining complete offline autonomy through automatic fallback to decision trees.

### Architecture

```
Equipment Telemetry
        ↓
Splunk MCP Server
        ↓
GeminiOrchestrator
        ├→ Gemini 1.5 Flash API (primary)
        │   └→ JSON Decision Response
        │
        ├→ Offline Decision Trees (fallback)
        │   └→ Identical Schema Response
        │
        ├→ Slack Webhook (HITL Alerts)
        │   └→ Red/Orange Alert Cards
        │
        └→ Audit Trail & Logging
            └→ Call History
```

## Key Features

### 1. Cloud API Integration
- **Gemini 1.5 Flash Model**: Low-latency, cost-effective LLM
- **Temperature 0.1**: Deterministic, consistent responses
- **JSON Response Mode**: Structured output matching our schema
- **Automatic Serialization**: Telemetry context automatically enriched

### 2. Seamless Fallback
- **No API Key Required**: System works without Gemini credentials
- **Offline Decision Trees**: Full triage capability offline
- **Schema Consistency**: Both paths return identical decision structure
- **Transparent to Caller**: No code changes needed for fallback

### 3. Human-in-the-Loop Workflow
- **Slack Integration**: Real-time alerts for CRITICAL/HIGH events
- **Action Buttons**: Approve/Override directly from Slack
- **Risk-Based Colors**: Red for CRITICAL, Orange for HIGH
- **Audit Trail**: All decisions logged for compliance

### 4. Splunk MCP Integration
- **Telemetry Queries**: Real-time equipment data access
- **Fault Log Context**: Historical failure patterns
- **Prediction Enrichment**: ML-powered failure forecasting
- **Site-Level Aggregation**: Multi-location awareness

## Usage

### Basic Setup

```python
from gemini_orchestrator import GeminiOrchestrator

# Initialize with .env file
orchestrator = GeminiOrchestrator(".env")

# Run triage loop
decision = orchestrator.run_triage_loop(
    query_type="operational",
    appliance_id="FZ-01"
)

print(f"Risk Level: {decision['risk_level']}")
print(f"Actions: {len(decision['action_plan'])}")
```

### Configuration

1. **Get API Keys**:
   ```bash
   # Gemini API: https://ai.google.dev/
   # Slack Webhook: https://api.slack.com/messaging/webhooks
   ```

2. **Create .env file**:
   ```bash
   cp .env.template .env
   # Edit .env with your credentials
   ```

3. **Environment Variables**:
   - `GEMINI_API_KEY`: Your Gemini API key (optional)
   - `SLACK_WEBHOOK_URL`: Your Slack webhook URL (optional)
   - `SPLUNK_MCP_URL`: Splunk MCP server address

### Three Triage Modes

#### 1. Operational Triage
Real-time equipment failure analysis during normal operations.

```python
decision = orchestrator.run_triage_loop(
    query_type="operational",
    appliance_id="FZ-01"
)
```

**Use Case**: Compressor failure, power loss, door breach detection  
**Expected Output**: CRITICAL decision with immediate actions  
**Example Decision ID**: `DEC-GEMINI-FZ-01-OP`

#### 2. Predictive Triage
Proactive analysis of failure trends and degradation patterns.

```python
decision = orchestrator.run_triage_loop(
    query_type="predictive",
    appliance_id="FZ-04"
)
```

**Use Case**: Temperature trending, sensor drift, maintenance planning  
**Expected Output**: HIGH/MEDIUM decision with preventive actions  
**Example Decision ID**: `DEC-GEMINI-FZ-04-PRED`

#### 3. Compliance Triage
Regulatory and access control investigation.

```python
decision = orchestrator.run_triage_loop(
    query_type="compliance",
    appliance_id="DD-01"
)
```

**Use Case**: Access anomalies, inventory discrepancies, DEA notifications  
**Expected Output**: CRITICAL decision with escalation steps  
**Example Decision ID**: `DEC-GEMINI-DD-01-COMP`

## API Reference

### GeminiOrchestrator

#### `__init__(env_file: str = ".env")`
Initialize orchestrator and load configuration.

**Parameters**:
- `env_file`: Path to .env configuration file

**Returns**: None

**Raises**: None (gracefully handles missing config)

#### `run_triage_loop(query_type, appliance_id, site_id)`
Main orchestration loop: telemetry → Gemini → alerts → audit trail.

**Parameters**:
- `query_type` (str): "operational" | "predictive" | "compliance"
- `appliance_id` (str, optional): Target appliance ID (e.g., "FZ-01")
- `site_id` (str, optional): Target site ID (e.g., "site_a")

**Returns**: Decision dictionary with schema:
```python
{
    "decision_id": "DEC-GEMINI-{appliance_id}",
    "analysis": "Detailed analysis string",
    "severity": 0.85,  # 0.0-1.0
    "risk_level": "CRITICAL|HIGH|MEDIUM|LOW",
    "recoverable": True/False,
    "requires_human_approval": True/False,
    "approval_message": "Action required if CRITICAL",
    "action_plan": [
        {
            "channel": "SAFETY|MAINTENANCE|COMPLIANCE|NOTIFICATION",
            "action": "ACTION_NAME",
            "params": { ... }
        }
    ]
}
```

#### `query_gemini(system_instruction, prompt, context_data, query_type)`
Query Gemini API with automatic fallback to offline trees.

**Parameters**:
- `system_instruction` (str): System prompt for Gemini
- `prompt` (str): User query with specific question
- `context_data` (dict): Telemetry and prediction context
- `query_type` (str): Query type for logging

**Returns**: Decision dictionary

**Fallback**: Returns `offline_triage()` result on API failure

#### `send_hitl_alert(decision, appliance_data)`
Post CRITICAL/HIGH alerts to Slack webhook.

**Parameters**:
- `decision` (dict): Decision dictionary
- `appliance_data` (dict): Equipment snapshot

**Returns**: Boolean (True if sent)

**Behavior**:
- RED color (#d62728) for CRITICAL
- ORANGE color (#ff7f0e) for HIGH
- Includes approve/override buttons
- Only sends if `requires_human_approval=True`

## Decision Flow

```
1. run_triage_loop() called
   ↓
2. Query Splunk MCP (mock_db in demo)
   ↓
3. Build Gemini prompt + system instruction
   ↓
4. Call Gemini API (or fallback to offline_triage)
   ↓
5. Parse JSON response
   ↓
6. Validate schema (ensure all required fields)
   ↓
7. If requires_human_approval: send_hitl_alert()
   ↓
8. Log decision to audit trail
   ↓
9. Return decision to caller
```

## Example Scenarios

### Scenario 1: Compressor Failure (Operational)

```python
decision = orchestrator.run_triage_loop(
    query_type="operational",
    appliance_id="FZ-01"
)

# Expected Output:
# {
#   "decision_id": "DEC-GEMINI-FZ-01",
#   "analysis": "CRITICAL: Compressor failure detected. Temperature rising 0.8C/hr...",
#   "severity": 0.96,
#   "risk_level": "CRITICAL",
#   "recoverable": True,
#   "requires_human_approval": True,
#   "approval_message": "APPROVAL REQUIRED: Authorize compressor replacement",
#   "action_plan": [
#     {"channel": "MAINTENANCE", "action": "EMERGENCY_COMPRESSOR_REPLACEMENT", ...},
#     {"channel": "SAFETY", "action": "PREPARE_PRODUCT_TRANSFER", ...},
#     {"channel": "NOTIFICATION", "action": "PAGE_ON_CALL", ...},
#     {"channel": "COMPLIANCE", "action": "INITIATE_DEVIATION_RESPONSE", ...}
#   ]
# }
```

### Scenario 2: Power Failure (Predictive)

```python
decision = orchestrator.run_triage_loop(
    query_type="predictive",
    appliance_id="FZ-04"
)

# Expected Output:
# {
#   "decision_id": "DEC-GEMINI-FZ-04",
#   "analysis": "CRITICAL: Power failure detected. Backup activation required...",
#   "severity": 0.98,
#   "risk_level": "CRITICAL",
#   "requires_human_approval": True,
#   "action_plan": [
#     {"channel": "MAINTENANCE", "action": "ACTIVATE_BACKUP_POWER", ...},
#     {"channel": "SAFETY", "action": "BEGIN_TEMPERATURE_MONITORING", ...},
#     ...
#   ]
# }
```

### Scenario 3: Access Anomaly (Compliance)

```python
decision = orchestrator.run_triage_loop(
    query_type="compliance",
    appliance_id="DD-01"
)

# Expected Output:
# {
#   "decision_id": "DEC-GEMINI-DD-01",
#   "analysis": "CRITICAL: Access anomaly detected. 55+ events in 24h...",
#   "severity": 0.90,
#   "risk_level": "CRITICAL",
#   "requires_human_approval": True,
#   "approval_message": "APPROVAL REQUIRED: Lock unit immediately, notify DEA",
#   "action_plan": [
#     {"channel": "SAFETY", "action": "LOCK_UNIT_IMMEDIATELY", ...},
#     {"channel": "NOTIFICATION", "action": "PAGE_SECURITY", ...},
#     {"channel": "COMPLIANCE", "action": "DEA_NOTIFICATION", ...},
#     ...
#   ]
# }
```

## Slack Integration

### Alert Format

When `requires_human_approval=True`, GeminiOrchestrator posts to Slack:

```
┌─────────────────────────────────────┐
│ 🚨 PharmaSense Alert — FZ-01       │
├─────────────────────────────────────┤
│                                     │
│ Risk Level:        CRITICAL         │
│ Severity:          96%              │
│ Equipment:         PharmaFreezer    │
│ Status:            COMPRESSOR_FAIL  │
│                                     │
│ Analysis:                           │
│ CRITICAL: Compressor failure       │
│ detected. Temperature rising 0.8°C  │
│ per hour...                         │
│                                     │
│ [ Approve Action ]  [ Override... ] │
│                                     │
└─────────────────────────────────────┘
```

### Alert Colors

- **#d62728** (Red): CRITICAL risk
- **#ff7f0e** (Orange): HIGH risk
- No alert: MEDIUM, LOW risk

## Offline Fallback

When Gemini API is unavailable or no API key configured:

```python
# Before (Online Mode)
orchestrator = GeminiOrchestrator(".env")
decision = orchestrator.run_triage_loop()
# → Queries Gemini API

# After (Offline Mode - if API fails or no key)
# → Automatically uses offline_triage() from pharma_sense_ai.py
# → Returns identical decision schema
# → No code changes needed
```

**Fallback is Transparent**: Caller doesn't need to know if response came from Gemini or offline trees.

## Performance

- **Gemini Query**: ~2-5 seconds (including network latency)
- **Offline Fallback**: <10ms (pure local computation)
- **Slack Alert**: ~1 second (webhook delivery)
- **Total Loop**: 3-6 seconds with Gemini, <100ms without

## Security

### API Key Protection

```python
# ✓ Good: Store in environment
GEMINI_API_KEY=sk-...

# ✗ Bad: Hardcoded
api_key = "sk-..."  # NEVER!
```

### Slack Webhook Protection

```bash
# Keep webhook URL private
echo "SLACK_WEBHOOK_URL=..." >> .env
```

### .env File

```bash
# Never commit .env to git
echo ".env" >> .gitignore
```

## Troubleshooting

### Issue: "No Gemini API key - using offline fallback"

**Cause**: `GEMINI_API_KEY` not set in environment or .env file

**Solution**:
1. Get API key from https://ai.google.dev/
2. Create .env file: `cp .env.template .env`
3. Add your key: `GEMINI_API_KEY=your_key_here`
4. Restart orchestrator

### Issue: "Slack webhook not configured"

**Cause**: `SLACK_WEBHOOK_URL` not set

**Solution**:
1. Get webhook from https://api.slack.com/messaging/webhooks
2. Add to .env: `SLACK_WEBHOOK_URL=https://hooks.slack.com/...`
3. Restart orchestrator

### Issue: Gemini returns non-JSON response

**Cause**: API limit, quota exceeded, or schema mismatch

**Solution**:
1. Check API status: https://ai.google.dev/
2. Verify quota at https://aistudio.google.com/
3. System automatically falls back to offline trees
4. Check logs for specific error

### Issue: Decisions always LOW risk

**Cause**: Equipment in nominal state

**Solution**:
1. Verify equipment profile is set to failure mode
2. Run `integration_test.py` to check fleet state
3. Check that simulation time is sufficient (>10 hours)

## Integration with Splunk

### HEC Integration (Optional)

```python
# In future version: log decisions to Splunk HEC
splunk_hec.post_event({
    "decision_id": decision['decision_id'],
    "risk_level": decision['risk_level'],
    "timestamp": datetime.now().isoformat(),
    "sourcetype": "pharmasense:decision"
})
```

### SPL Search Examples

```spl
# Find all CRITICAL decisions
sourcetype=pharmasense:decision risk_level=CRITICAL

# Count decisions by risk level
sourcetype=pharmasense:decision | stats count by risk_level

# Timeline of approvals needed
sourcetype=pharmasense:decision requires_human_approval=true | timechart count by appliance_id
```

## Related Files

- **pharma_sense_ai.py** - Core simulation engine and decision trees
- **offline_decisions.py** - Example offline decision scenarios
- **examples.py** - Integration patterns
- **.env.template** - Configuration template

## License

Licensed under the Apache License, Version 2.0. See LICENSE file for details.

---

**Version**: 1.0  
**Updated**: 2026-06-15  
**Status**: Production Ready
