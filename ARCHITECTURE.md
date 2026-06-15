# Architecture Documentation: PharmaSense AI

## 1. System Overview

PharmaSense AI is an enterprise-grade cold chain and drug safety monitoring platform that protects critical medical assets by uniting physics-based simulation telemetry, autonomous artificial intelligence, and centralized compliance auditing. The architecture features an offline-first design pattern combining hardcoded, regulatory-compliant deterministic local decision trees with the cognitive orchestration capabilities of Google's Gemini 1.5 Flash. By continuously processing high-frequency data from specialized pharmaceutical storage environments, the platform proactively mitigates risk, executes human-in-the-loop safety loops via Slack, and ensures full GxP and WHO regulatory audit alignment through real-time telemetry indexing into Splunk.

---

## 2. Data Flow

The platform processes data sequentially across a multi-tier closed loop. Telemetry moves from point-of-origin hardware to persistent centralized storage, feeds into the AI reasoning models, and is returned to the compliance log with exact contextual enrichment.

```text
┌──────────────┐     ┌──────────────────┐     ┌────────────────┐     ┌──────────────┐
│  Appliances  │ ──> │  simulation.py   │ ──> │   Splunk HEC   │ ──> │ Splunk Index │
│ (Sensors/IO) │     │ (Physics Engine) │     │ (urllib client)│     │(pharmasense) │
└──────────────┘     └──────────────────┘     └────────────────┘     └──────┬───────┘
                                                                            │
┌──────────────┐     ┌──────────────────┐     ┌────────────────┐            │
│   Decision   │ <── │   Gemini Orch    │ <── │   MCP Server   │ <──────────┘
│ (Structured) │     │ (Cloud/Fallback) │     │ (Context Query)│
└──────┬───────┘     └──────────────────┘     └────────────────┘
       │
       ├──> [Risk = CRITICAL] ──> HITL Slack Alert ──┐
       │                                             ▼
       └──> [Risk < CRITICAL] ──> Auto-Action ──> Logged Back to Splunk

```

---

## 3. Components

| Component | File | Responsibility | Owner |
| --- | --- | --- | --- |
| **Simulation Engine** | `pharma_sense_ai.py` | Models realistic multi-profile thermodynamic behaviors and localized failure states across freezer, dispenser, and blood storage equipment. | Core Systems Engineering |
| **Gemini Orchestrator** | `gemini_orchestrator.py` | Formulates deep context prompt wrappers, queries the Model Context Provider, executes structured LLM parsing, and initiates emergency actions. | AI Infrastructure Team |
| **Splunk HEC Client** | `splunk_hec_client.py` | Serializes telemetry objects and manages high-throughput, dependency-free network batch transmissions over TLS. | Observability & Security |
| **Integration Layer** | `splunk_integration_example.py` | Acts as the system runtime controller executing localized scenarios, failure generation, and cross-tier automation loops. | Solutions Architecture |

---

## 4. Telemetry Schema

Every individual hardware event targeted for transmission to the Splunk HTTP Event Collector satisfies a comprehensive JSON schema representation. The standard schema fields are defined below:

* `timestamp` (string): ISO 8601 formatted timestamp indicating moment of telemetry capture.
* `appliance_id` (string): Unique identifier corresponding to physical asset asset tag (e.g., `FZ-01`).
* `appliance_type` (string): Equipment classification, restricted to `PharmaFreezer`, `DrugDispenser`, or `BloodStorage`.
* `site_id` (string): Identifies the geographical or organizational facility location mapping the asset.
* `status` (string): Current equipment state-machine enumeration metric (e.g., `NOMINAL`, `COMPRESSOR_FAIL`, `TEMP_CRITICAL`).
* `temp_c` (float): The actual displayed operational temperature tracking metric in degrees Celsius.
* `humidity_pct` (float): Percentage representation denoting internal humidity measurements.
* `risk_level` (string): Evaluated platform status categorization (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
* `severity` (float): Normalized floating-point representation scaling severity threshold indexes between `0.0` and `1.0`.
* `predicted_failure` (string): Foreseen architectural asset issue identified by heuristic trend evaluation.
* `predicted_failure_confidence` (float): Percentage certainty metrics expressing precision confidence levels (`0.85` - `0.98`).
* `time_to_critical_hours` (float): Remaining useful life estimate indicating hours remaining until safe limits are crossed.
* `recommended_action` (string): Next-step tactical operational instructions mapping to standard WHO protocols.
* `requires_human_approval` (boolean): Flag dictating mandatory routing through interactive authorization firewalls.

---

## 5. Predictive Math

### Remaining Useful Life (RUL) Calculation

When the internal prediction architecture tracks an upward or downward parameter excursion pattern drifting beyond nominal boundaries, the exact remaining useful life timeline estimation is computed using the following derivative relationship:

$$\text{hours\_to\_critical} = \frac{\text{critical\_temp} - \text{current\_temp}}{\text{warming\_rate}}$$

### Warming Rate Estimation

Rather than evaluating instantaneous sensor point data, the platform determines the underlying `warming_rate` using an active linear regression model calculated across the final rolling window of 3 consecutive telemetry intervals ($t_{-2}, t_{-1}, t_{0}$):

$$\text{warming\_rate} = \frac{n\sum(t \cdot T) - \sum t \sum T}{n\sum(t^2) - (\sum t)^2} \quad \text{where } n=3$$

### Unified Risk Score Calculation

Asset status rankings depend on a balanced calculation model merging active baseline anomalies, trajectory speeds, and location severity weightings into a single normalized index value:

$$\text{Risk Score} = (0.5 \times \text{temp\_norm}) + (0.3 \times \text{trend\_norm}) + (0.2 \times \text{site\_criticality})$$

* $\text{temp\_norm}$: The variance offset of the current asset temperature relative to its authorized WHO target range.
* $\text{trend\_norm}$: Accelerated parameter variation behavior derived directly from the linear regression calculation slope.
* $\text{site\_criticality}$: Static priority constant mapped to specific infrastructure zones (e.g., intensive clinical units vs general distribution warehouses).

---

## 6. Decision Routing

Platform handling actions follow strict operational matrix routing guidelines based on the assessed threat score:

| Risk Level | Routing | Human Needed |
| --- | --- | --- |
| **CRITICAL** | `ESCALATE_HITL` | Yes |
| **HIGH** | `AUTO_ACTION + NOTIFY` | No |
| **MEDIUM** | `SCHEDULE_MAINTENANCE` | No |
| **LOW** | `LOG_ONLY` | No |

---

## 7. Splunk Integration

### Infrastructure Topology

* **Target Index:** `pharmasense`
* **Sourcetypes:**
* `pharmasense:telemetry` — High-frequency environmental sensor data streams tracking hardware metrics.
* `pharmasense:decision` — Enriched analytical outputs originating from the cloud or local fallback decision trees.
* `pharmasense:alert` — Incident logs recording critical exceptions and corresponding interactive notification events.



### Primary Compliance Dashboard Panels

1. **Active GxP Temperature Excursions:** Single-value KPI panel displaying immediate instances of temperature parameter breaches requiring corrective actions.
2. **Fleet Remaining Useful Life (RUL) Forecast:** Time-series projection tracking operational timelines for assets approaching failure thresholds, sorting maintenance prioritizations.
3. **Orchestration Path Efficiency:** Structural ratio chart tracking reliance on live Gemini cloud processing loops versus local fallback engines to confirm absolute uptime connectivity.
4. **HITL Slack Action Audit Trail:** Regulatory validation matrix auditing all manual `Approve` or `Override` overrides for absolute accountability verification.

---

## 8. Offline Mode

To guarantee continuous protection for medical assets during network disruptions or API availability challenges, the platform includes an embedded structural mirroring layer. When the core orchestrator identifies a connection failure or timeout event, execution drops immediately to localized deterministic decision tree models.

```text
[Live Cloud Mode]       ──> Resolves via Gemini LLM Context Engine ──┐
                                                                     ├─> Identical JSON Contract
[Autonomous Fallback]   ──> Resolves via Local Physics Rule Trees   ──┘

```

These local fallback structures use conditional checks based directly on WHO vaccine storage standards and thermodynamic thresholds. Because the local fallback functions return data formatted to the same exact unified JSON response contract as the cloud-based Gemini system, the downstream tracking pipelines, notification hooks, and Splunk indexers can continue to process the information without code adjustments or data transformation steps.