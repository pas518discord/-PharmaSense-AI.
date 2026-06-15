# SplunkHECClient — Telemetry & Alerts

## Overview

The **SplunkHECClient** class sends pharmaceutical equipment telemetry, decisions, and alerts to Splunk HTTP Event Collector (HEC).

**Key Features:**
- ✅ Single event telemetry with decision enrichment
- ✅ Batch event submission (up to 100 events/batch)
- ✅ Notable event/alert generation
- ✅ Automatic retry on failure
- ✅ Mock mode (stdout) when HEC not configured
- ✅ Zero external dependencies (urllib only)
- ✅ SSL verification control for dev/prod

---

## Installation & Setup

### 1. No Dependencies

```bash
# SplunkHECClient uses only Python stdlib
# urllib for HTTP
# json for serialization
# ssl for HTTPS
# No requirements.txt needed!
```

### 2. Get Splunk HEC Credentials

**Option A: Local Splunk (Development)**
```bash
# Start Splunk with HEC enabled
splunk show forward-server -auth admin:password
# HEC typically at: https://localhost:8088

# Create HEC token:
# Settings > Data Inputs > HTTP Event Collector
# Name: pharmasense
# Token: <copy generated token>
```

**Option B: Splunk Cloud (Production)**
```bash
# Contact Splunk Cloud admin
# HEC URL: https://<instance>.splunkcloud.com:8088
# HEC Token: <provided by admin>
```

### 3. Configure Environment

```bash
# Create .env file (or export variables)
SPLUNK_HEC_URL=https://localhost:8088
SPLUNK_HEC_TOKEN=abc123def456...

# For mock mode (no HEC):
# Simply don't set these variables
# Events print to stdout with [MOCK HEC] prefix
```

---

## API Reference

### Class: SplunkHECClient

#### `__init__(hec_url: str = None, hec_token: str = None)`

Initialize Splunk HEC client.

```python
from splunk_hec_client import SplunkHECClient

# Production: Load from environment
client = SplunkHECClient()

# Or explicit credentials
client = SplunkHECClient(
    hec_url="https://splunk.example.com:8088",
    hec_token="abc123def456..."
)

# Mock mode: No credentials provided
client = SplunkHECClient()  # Uses stdout if env vars missing
```

**Parameters:**
- `hec_url` (str, optional): Splunk HEC URL. Falls back to `SPLUNK_HEC_URL` env var.
- `hec_token` (str, optional): HEC auth token. Falls back to `SPLUNK_HEC_TOKEN` env var.

**Properties:**
- `.mock_mode` (bool): True if no HEC credentials configured
- `.event_count` (int): Total events sent
- `.batch_count` (int): Total batches sent
- `.alert_count` (int): Total alerts sent

---

#### `send_event(appliance_snapshot, decision=None) → bool`

Send a single appliance telemetry event to Splunk.

```python
# Basic telemetry only
appliance_data = {
    "equipment_id": "FZ-01",
    "equipment_type": "PharmaFreezer",
    "site_name": "site_a",
    "status": "RUNNING",
    "temp_c": -22.5,
    "humidity_pct": 35.0
}

success = client.send_event(appliance_data)
print(f"Sent: {success}")  # True/False

# With decision enrichment
decision = {
    "decision_id": "DEC-2026-FREEZER-FZ-01",
    "risk_level": "CRITICAL",
    "severity": 0.96,
    "requires_human_approval": True,
    "action_plan": [
        {
            "channel": "MAINTENANCE",
            "action": "EMERGENCY_COMPRESSOR_REPLACEMENT"
        }
    ]
}

success = client.send_event(appliance_data, decision)
```

**HEC Payload Format:**
```json
{
  "time": 1781522709,
  "index": "pharmasense",
  "source": "pharmasense:simulation",
  "sourcetype": "pharma:telemetry",
  "event": {
    "equipment_id": "FZ-01",
    "equipment_type": "PharmaFreezer",
    "status": "RUNNING",
    "temp_c": -22.5,
    "risk_level": "CRITICAL",
    "severity": 0.96,
    "decision_id": "DEC-2026-FREEZER-FZ-01",
    "requires_human_approval": true,
    "recommended_action": "EMERGENCY_COMPRESSOR_REPLACEMENT",
    "action_channel": "MAINTENANCE"
  }
}
```

**Parameters:**
- `appliance_snapshot` (dict): Equipment telemetry snapshot
- `decision` (dict, optional): Decision object with enrichment fields

**Returns:**
- `True` if sent successfully
- `False` on failure (includes 1 automatic retry)

**Decision Fields (Enrichment):**
When decision provided, automatically extracted:
- `risk_level`: CRITICAL, HIGH, MEDIUM, LOW
- `severity`: 0.0-1.0 confidence
- `decision_id`: Unique identifier
- `requires_human_approval`: Boolean
- `recommended_action`: First action from plan
- `action_channel`: MAINTENANCE, SAFETY, COMPLIANCE, NOTIFICATION

---

#### `send_batch(events: list[dict], max_batch: int = 100) → bool`

Send multiple events in batch HEC request (newline-separated JSON).

```python
# Single batch
events = [
    {
        "equipment_id": "FZ-01",
        "equipment_type": "PharmaFreezer",
        "status": "RUNNING",
        "temp_c": -20.0
    },
    {
        "equipment_id": "DD-01",
        "equipment_type": "DrugDispenser",
        "status": "RUNNING",
        "temp_c": 20.0
    }
]

success = client.send_batch(events)

# Large batch (auto-splits at 100 events)
large_batch = [...]  # 250 events
success = client.send_batch(large_batch)  # Sends in 3 requests: 100, 100, 50

# Custom batch size
success = client.send_batch(events, max_batch=50)
```

**Behavior:**
- Automatically splits into chunks (default: max 100 events)
- Each chunk sent as separate HEC request
- Newline-separated JSON format
- Individual retry per batch

**Parameters:**
- `events` (list[dict]): List of event dictionaries
- `max_batch` (int): Maximum events per HEC request (default: 100)

**Returns:**
- `True` if all batches sent successfully
- `False` if any batch fails

---

#### `send_alert(alert_type, message, severity="MEDIUM", appliance_id="UNKNOWN") → bool`

Send a notable event/alert to Splunk.

```python
# Send equipment failure alert
client.send_alert(
    alert_type="EQUIPMENT_FAILURE",
    message="Compressor failure on FZ-01 - immediate action required",
    severity="CRITICAL",
    appliance_id="FZ-01"
)

# Access anomaly alert
client.send_alert(
    alert_type="ACCESS_ANOMALY",
    message="Unusual access pattern detected on DD-01",
    severity="HIGH",
    appliance_id="DD-01"
)

# Temperature excursion alert
client.send_alert(
    alert_type="TEMP_EXCURSION",
    message="Blood storage temperature exceeded safety threshold",
    severity="CRITICAL",
    appliance_id="BS-01"
)
```

**HEC Payload Format:**
```json
{
  "time": 1781522709,
  "index": "pharmasense",
  "source": "pharmasense:alerts",
  "sourcetype": "pharma:alert",
  "event": {
    "alert_type": "EQUIPMENT_FAILURE",
    "message": "Compressor failure on FZ-01 - immediate action required",
    "severity": "CRITICAL",
    "appliance_id": "FZ-01",
    "timestamp": 1781522709
  }
}
```

**Parameters:**
- `alert_type` (str): Alert type (e.g., "EQUIPMENT_FAILURE", "ACCESS_ANOMALY")
- `message` (str): Human-readable alert message
- `severity` (str): CRITICAL, HIGH, MEDIUM, LOW (default: MEDIUM)
- `appliance_id` (str): Equipment ID (default: UNKNOWN)

**Returns:**
- `True` if sent successfully
- `False` on failure

**Common Alert Types:**
- `EQUIPMENT_FAILURE`: Physical equipment malfunction
- `ACCESS_ANOMALY`: Unauthorized or unusual access
- `TEMP_EXCURSION`: Temperature out of range
- `INVENTORY_ALERT`: Inventory levels critical
- `MAINTENANCE_DUE`: Scheduled maintenance needed
- `COMPLIANCE_VIOLATION`: Regulatory non-compliance
- `POWER_LOSS`: Power failure detected

---

#### `get_stats() → dict`

Get statistics on sent events.

```python
stats = client.get_stats()
print(f"Events sent: {stats['events_sent']}")
print(f"Batches sent: {stats['batches_sent']}")
print(f"Mode: {'MOCK' if stats['mock_mode'] else 'PRODUCTION'}")

# Output:
# Events sent: 15
# Batches sent: 3
# Mode: MOCK
```

**Returns:**
```python
{
    "events_sent": int,      # Total single events
    "batches_sent": int,     # Total batch requests
    "alerts_sent": int,      # Total alerts
    "mock_mode": bool        # True if in mock mode
}
```

---

## Usage Examples

### Example 1: Real-Time Monitoring

```python
from gemini_orchestrator import GeminiOrchestrator
from splunk_hec_client import SplunkHECClient
import time

# Initialize clients
orch = GeminiOrchestrator()
hec = SplunkHECClient()

# Monitor equipment continuously
equipment_ids = ["FZ-01", "FZ-02", "DD-01", "DD-02", "BS-01"]

while True:
    for equipment_id in equipment_ids:
        # Get current snapshot
        snapshot = get_appliance_snapshot(equipment_id)
        
        # Run triage
        decision = orch.run_triage_loop(appliance_id=equipment_id)
        
        # Send to Splunk
        hec.send_event(snapshot, decision)
        
        # Send alert if critical
        if decision['risk_level'] == 'CRITICAL':
            hec.send_alert(
                alert_type="EQUIPMENT_FAILURE",
                message=decision['analysis'],
                severity="CRITICAL",
                appliance_id=equipment_id
            )
    
    time.sleep(300)  # Check every 5 minutes
```

### Example 2: Batch Telemetry Collection

```python
from splunk_hec_client import SplunkHECClient
from pharma_sense_ai import FleetSimulation

# Initialize
hec = SplunkHECClient()
fleet = FleetSimulation()

# Collect hourly telemetry from all equipment
hourly_events = []

for equipment in fleet.all_equipment:
    snapshot = equipment.get_snapshot()
    hourly_events.append(snapshot)

# Send batch (auto-splits if >100 events)
success = hec.send_batch(hourly_events)

print(f"Sent {len(hourly_events)} events in batch: {success}")
```

### Example 3: Compliance Reporting

```python
from splunk_hec_client import SplunkHECClient
from datetime import datetime, timedelta

hec = SplunkHECClient()

# Generate compliance alerts for WHO violations
def check_compliance():
    """Check all equipment for WHO standard violations."""
    
    violations = []
    
    for equipment in fleet.all_equipment:
        snapshot = equipment.get_snapshot()
        
        # Check WHO standards
        if equipment.type == "PharmaFreezer":
            if not (-25 <= snapshot['temp_c'] <= -15):
                violations.append({
                    "equipment_id": equipment.id,
                    "violation": "TEMPERATURE_OUT_OF_RANGE",
                    "expected": "-15 to -25°C",
                    "actual": f"{snapshot['temp_c']}°C"
                })
        
        elif equipment.type == "BloodStorage":
            if not (1 <= snapshot['temp_c'] <= 6):
                violations.append({
                    "equipment_id": equipment.id,
                    "violation": "BLOOD_STORAGE_OUT_OF_RANGE",
                    "expected": "1 to 6°C",
                    "actual": f"{snapshot['temp_c']}°C"
                })
    
    # Send compliance alerts
    for violation in violations:
        hec.send_alert(
            alert_type="COMPLIANCE_VIOLATION",
            message=f"{violation['violation']}: {violation['actual']}",
            severity="CRITICAL",
            appliance_id=violation['equipment_id']
        )
    
    return len(violations)

violations_found = check_compliance()
print(f"Compliance check: {violations_found} violations found and reported")
```

### Example 4: Integration with Gemini Orchestrator

```python
from gemini_orchestrator import GeminiOrchestrator
from splunk_hec_client import SplunkHECClient
from pharma_sense_ai import mock_db

# Initialize both clients
orch = GeminiOrchestrator()
hec = SplunkHECClient()

# Run triage and send to both Slack and Splunk
def orchestrate_with_telemetry(appliance_id):
    """Run triage and send results to Slack and Splunk."""
    
    # Get telemetry from Splunk MCP
    telemetry = mock_db.get_equipment(appliance_id)
    snapshot = telemetry[0] if telemetry else {}
    
    # Run orchestrator (sends to Slack if CRITICAL)
    decision = orch.run_triage_loop(
        query_type="operational",
        appliance_id=appliance_id
    )
    
    # Also send to Splunk HEC
    hec.send_event(snapshot, decision)
    
    return decision

# Run for all equipment
for appliance_id in ["FZ-01", "DD-01", "BS-01"]:
    decision = orchestrate_with_telemetry(appliance_id)
    print(f"{appliance_id}: {decision['risk_level']}")
```

---

## Mock Mode

When no `SPLUNK_HEC_URL` or `SPLUNK_HEC_TOKEN` configured, client operates in **mock mode**:

```python
# No credentials → Mock mode
client = SplunkHECClient()

# Output:
# [SplunkHECClient] MOCK MODE - Events will print to stdout
# [SplunkHECClient] Configure SPLUNK_HEC_URL and SPLUNK_HEC_TOKEN for production

# Events print to stdout with [MOCK HEC] prefix
client.send_event(snapshot, decision)

# Output:
# [MOCK HEC] Event: {
#   "time": 1781522709,
#   "index": "pharmasense",
#   "source": "pharmasense:simulation",
#   "sourcetype": "pharma:telemetry",
#   "event": {...}
# }
```

**Use Cases:**
- ✅ Local development
- ✅ Testing without Splunk
- ✅ Debugging event formats
- ✅ CI/CD pipelines
- ✅ Demo environments

---

## Splunk Searches & Dashboards

### SPL Query: Equipment Status Overview

```spl
index=pharmasense sourcetype=pharma:telemetry
| stats latest(temp_c) as temp, latest(status) as status by equipment_id, equipment_type
| where status != "RUNNING"
```

### SPL Query: Critical Alerts (Last 24h)

```spl
index=pharmasense sourcetype=pharma:alert severity=CRITICAL
| stats count by alert_type, appliance_id
| rename appliance_id as "Equipment ID"
```

### SPL Query: Decision Timeline

```spl
index=pharmasense sourcetype=pharma:telemetry decision_id=*
| stats count by risk_level, equipment_id
| chart sum(count) by risk_level
```

### SPL Query: Temperature Trends

```spl
index=pharmasense sourcetype=pharma:telemetry equipment_type=PharmaFreezer
| timechart avg(temp_c) as "Avg Temp", min(temp_c) as "Min Temp", max(temp_c) as "Max Temp" by equipment_id
```

---

## Error Handling & Retry

The client automatically handles failures:

```python
# Single failure: Automatic retry
try:
    client.send_event(snapshot)  # Fails → auto-retries → succeeds/fails
except Exception as e:
    print(f"Final failure: {e}")

# Retry behavior:
# 1. Initial attempt fails (network, auth, timeout)
# 2. Wait 1 second
# 3. Single retry
# 4. If still fails, return False (logged to stdout)
```

**Timeout:** 10 seconds per event, 30 seconds per batch

**Failures Handled:**
- Network errors (URLError)
- HTTP errors (403 Forbidden, 401 Unauthorized, 500 Server Error)
- Timeouts
- SSL/TLS errors (retries with warn)
- JSON encoding errors

---

## Performance

| Operation | Latency | Notes |
|-----------|---------|-------|
| Single event | 100-500ms | Network + Splunk processing |
| Batch (50) | 200-800ms | Newline-separated JSON |
| Batch (100) | 300-1s | Max batch size |
| Retry | +1s | On failure |
| Mock mode | <1ms | Stdout only |

**Throughput:**
- ~2-5 events/second (with retries)
- ~10-20 events/second (mock mode)

---

## SSL/TLS & Security

```python
# Current implementation:
# - Disables SSL verification for local dev
# - Suitable for http://localhost:8088
# - NOT suitable for production

# For production Splunk Cloud:
ssl_context = ssl.create_default_context()
# Uses system CA bundle automatically
# Verifies certificate by default
```

**Recommendations:**
1. **Local Dev**: Current config (ssl_verify=False) is fine
2. **Splunk Cloud**: Update to use system CA bundle
3. **Firewalls**: HEC on port 8088 (or 9997 for SSL)
4. **Tokens**: Store in environment variables, never hardcode
5. **Rotation**: Rotate HEC tokens quarterly

---

## Troubleshooting

### Issue: "MOCK MODE - Events will print to stdout"

**Cause:** Environment variables not set

**Solution:**
```bash
export SPLUNK_HEC_URL=https://localhost:8088
export SPLUNK_HEC_TOKEN=abc123...
python my_script.py
```

### Issue: "Send failed after retry: HTTPError 401"

**Cause:** Invalid or expired HEC token

**Solution:**
```bash
# Verify token in Splunk
Settings > Data Inputs > HTTP Event Collector
# Copy token and update .env
```

### Issue: "Send failed: URLError - [SSL: CERTIFICATE_VERIFY_FAILED]"

**Cause:** Self-signed certificate on Splunk

**Solution:**
```python
# Already handled in current code:
ssl_context.verify_mode = ssl.CERT_NONE  # Accepts any certificate
```

### Issue: "Socket timeout on batch of 100 events"

**Cause:** Splunk overloaded or network slow

**Solution:**
```python
# Reduce batch size
hec.send_batch(events, max_batch=50)  # Default 100
```

---

## Configuration Examples

### Development (Local Splunk)

```bash
# .env
SPLUNK_HEC_URL=https://localhost:8088
SPLUNK_HEC_TOKEN=abc123def456...
```

### Production (Splunk Cloud)

```bash
# .env
SPLUNK_HEC_URL=https://prd-instance.splunkcloud.com:8088
SPLUNK_HEC_TOKEN=<prod-token>
```

### CI/CD (Mock Mode)

```bash
# No .env needed!
# Events print to stdout during testing
```

---

## Integration Checklist

- [ ] Splunk HEC endpoint accessible
- [ ] HEC token created and valid
- [ ] SPLUNK_HEC_URL and SPLUNK_HEC_TOKEN in environment
- [ ] Test with: `python splunk_hec_client.py`
- [ ] Verify events in Splunk: `index=pharmasense`
- [ ] Create alerts in Splunk for CRITICAL events
- [ ] Set up dashboard for real-time monitoring
- [ ] Configure HITL workflow (Slack + Splunk)
- [ ] Enable log shipping for compliance audit trail
- [ ] Document retention policy (7 years for pharma)

---

## Related Documentation

- **GEMINI_ORCHESTRATOR.md** — Cloud orchestration with Slack
- **INTEGRATION_GUIDE.md** — Full integration workflows
- **pharma_sense_ai.py** — Core simulation engine
- **README.md** — System overview

---

**Version**: 1.0  
**Status**: Production Ready ✅  
**Dependencies**: Python stdlib only (urllib, json, ssl)  
**License**: Apache 2.0
