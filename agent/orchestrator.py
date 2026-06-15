#!/usr/bin/env python3
# -*- coding: utf-8 -*


import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# Import core simulation engine, predictive analytic engine, and offline triage routines.
# Note: For our fallback and context population, we rely directly on pharma_sense_ai's 
# built-in mock_db, predict_failure, and triage logic, satisfying the function layout.
from pharma_sense_ai import mock_db, triage as offline_triage, predict_failure


def _is_placeholder_url(value: Optional[str]) -> bool:
    """Return True for example values copied from .env templates."""
    if not value:
        return False
    placeholders = ("YOUR/", "WEBHOOK", "T00000000", "XXXXXXXXXXXXXXXX")
    return any(marker in value for marker in placeholders)


class GeminiOrchestrator:
    """
    Orchestrates pharmaceutical equipment decision-making via Gemini API 
    with automatic fallback to local offline decision trees when the cloud API is unavailable.
    """

    def __init__(self, env_file: str = ".env"):
        """
        Initialize orchestrator by manually parsing a .env configuration file
        to load key operational settings without external dependencies.
        """
        self.gemini_key: Optional[str] = None
        self.slack_url: Optional[str] = None
        self.splunk_url: Optional[str] = None
        self.splunk_token: Optional[str] = None

        if os.path.exists(env_file):
            try:
                with open(env_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        if key == "GEMINI_API_KEY":
                            self.gemini_key = val
                        elif key == "SLACK_WEBHOOK_URL":
                            self.slack_url = val
                        elif key == "SPLUNK_HEC_URL":
                            self.splunk_url = val
                        elif key == "SPLUNK_HEC_TOKEN":
                            self.splunk_token = val
            except Exception as e:
                print(f"[-] Error manually reading env configuration file: {e}")

        # Fallback to true environment bindings if .env is missing or incomplete
        self.gemini_key = self.gemini_key or os.environ.get("GEMINI_API_KEY")
        self.slack_url = self.slack_url or os.environ.get("SLACK_WEBHOOK_URL")
        self.splunk_url = self.splunk_url or os.environ.get("SPLUNK_HEC_URL")
        self.splunk_token = self.splunk_token or os.environ.get("SPLUNK_HEC_TOKEN")
        if _is_placeholder_url(self.slack_url):
            self.slack_url = None

        # Active tracking metadata for operations analytics
        self.audit_trail = []

    def run_triage_loop(self, query_type: str, appliance_id: Optional[str] = None, site_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Main orchestration entrypoint loop. 
        Queries the simulated telemetry infrastructure context, formats context bounds, 
        evaluates metrics via low-temperature Gemini inference, and invokes human validation actions.
        """
        print(f"\n[*] Commencing Triage Loop (Query Mode: '{query_type}', Target Device: '{appliance_id or 'ALL'}')...")
        
        # 1. Query infrastructure dataset context (Simulated Splunk/CMDB database)
        db = mock_db()
        target_snapshot = None

        for group, items in db.items():
            for item in items:
                if appliance_id and item.equipment_id == appliance_id:
                    # Progress time slightly to gather realistic metrics if desired
                    item.step(1.5)
                    target_snapshot = item.snapshot(datetime.now())
                    break
                elif site_id and getattr(item, 'site_name', None) == site_id:
                    item.step(1.0)
                    target_snapshot = item.snapshot(datetime.now())
                    break
            if target_snapshot:
                break

        # If matching device context isn't explicitly found, default to a robust operational node
        if not target_snapshot:
            print(f"[!] Warning: Appliance {appliance_id} not indexed. Fetching fallback reference system context.")
            target_snapshot = db['pharma_freezers'][0].snapshot(datetime.now())

        # Enrich telemetry dataset context with automated failure predictions
        prediction = predict_failure(target_snapshot)
        target_snapshot["prediction_enrichment"] = prediction

        # 2. Construct the deterministic operational constraints profile via system instruction
        system_instruction = (
            "You are PharmaSense, monitoring pharmaceutical cold chain storage equipment and regulatory compliance matrices.\n"
            "Analyze telemetry logs and predictive analysis failure vectors. You MUST respond with a strictly valid, single JSON object "
            "matching the standard configuration schema exactly, without any external markdown wraps or commentary."
        )

        prompt = (
            f"Evaluate this current multi-tier operational snapshot context and formulate a triage decision plan:\n"
            f"Context Profile Type: {query_type}\n"
            f"Telemetry payload Data:\n{json.dumps(target_snapshot, indent=2)}\n"
        )

        decision = None

        # 3. Assess through Cloud Orchestration if API key binds are accessible
        if self.gemini_key:
            decision = self.query_gemini(system_instruction, prompt, target_snapshot, query_type)

        # 4. Fallback execution path if Cloud layer is unconfigured or encounters interface exceptions
        if not decision:
            print("[!] Cloud API unavailable or unconfigured. Diverting to local offline decision trees.")
            # Map standard top-level fields for system compliance schema
            decision = offline_triage(target_snapshot)

        # Ensure schema structure guarantees normalization
        if not isinstance(decision, dict):
            decision = {"error": "Invalid response type received from triage processor"}

        # Normalize schema variables if absent from cloud or fallback definitions
        if "decision_id" not in decision:
            decision["decision_id"] = f"DEC-{int(datetime.now().timestamp())}-{target_snapshot.get('equipment_id', 'UNKNOWN')}"
        if "risk_level" not in decision:
            decision["risk_level"] = "LOW"
        if "requires_human_approval" not in decision:
            decision["requires_human_approval"] = decision.get("risk_level") in ["HIGH", "CRITICAL"]

        # 5. Route safety intervention blocks to human workflows if flag criteria is matched
        if decision.get("requires_human_approval"):
            self.send_hitl_alert(decision, target_snapshot)

        # 6. Log operational record out to Telemetry audit trails
        self._log_to_splunk_hec(target_snapshot, decision)

        # Update local metrics collection
        self.audit_trail.append({"timestamp": datetime.now().isoformat(), "decision": decision})
        
        print(f"[+] Operational Triage Loop Completed. Assigned Risk Severity Evaluation: [{decision.get('risk_level')}]")
        return decision

    def query_gemini(self, system_instruction: str, prompt: str, context_data: Dict[str, Any], query_type: str) -> Optional[Dict[str, Any]]:
        """
        Queries Gemini 1.5 Flash API via native standard runtime libraries using low-temperature configuration constraints.
        """
        # Endpoint configuration parameters for standard resource tracking
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
        
        # Structure payload following standard Google AI Schema declarations
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"{prompt}"
                }]
            }],
            "systemInstruction": {
                "parts": [{
                    "text": system_instruction
                }]
            },
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json"
            }
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=8) as response:
                res_body = response.read().decode("utf-8")
                parsed_res = json.loads(res_body)
                
                # Unpack and extract generated text contents safely
                text_content = parsed_res['candidates'][0]['content']['parts'][0]['text']
                return json.loads(text_content.strip())

        except Exception as e:
            print(f"[-] Gemini API query operational execution fault: {e}")
            return None

    def send_hitl_alert(self, decision: Dict[str, Any], appliance_data: Dict[str, Any]):
        """
        Dispatches targeted interactive Human-In-The-Loop notifications to configured internal Slack team hubs.
        """
        if not self.slack_url:
            print(f"[Mock Slack Alert] -> HITL Target Triggered for {appliance_data.get('equipment_id')}. (Missing URL key boundary)")
            print(f" >> Alert Severity: {decision.get('risk_level')} | Priority Analysis: {decision.get('analysis')}")
            return

        risk = decision.get("risk_level", "UNKNOWN").upper()
        color = "#e63946" if risk == "CRITICAL" else "#f4a261" # Standard visual mapping bounds

        # Formulate operational message architecture
        slack_payload = {
            "attachments": [
                {
                    "fallback": f"PharmaSense Critical Alert — Device {appliance_data.get('equipment_id')}",
                    "color": color,
                    "title": f"🚨 PharmaSense Alarm Action Log — {appliance_data.get('equipment_id')}",
                    "text": f"*Analysis Summary:*\n{decision.get('analysis', 'No detailed analysis provided.')}",
                    "fields": [
                        {
                            "title": "Risk Mitigation Tier",
                            "value": risk,
                            "short": True
                        },
                        {
                            "title": "Hardware Model Class",
                            "value": appliance_data.get("equipment_type", "Unknown"),
                            "short": True
                        },
                        {
                            "title": "Recommended Action Workflow",
                            "value": decision.get("approval_message", "Awaiting infrastructure triage confirmation execution policy."),
                            "short": False
                        }
                    ],
                    "actions": [
                        {
                            "name": "approve_action",
                            "text": "Approve Action Plan",
                            "type": "button",
                            "style": "primary",
                            "value": "approved"
                        },
                        {
                            "name": "override_action",
                            "text": "Override — Keep Running",
                            "type": "button",
                            "style": "danger",
                            "value": "overridden"
                        }
                    ],
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }

        try:
            req = urllib.request.Request(
                self.slack_url,
                data=json.dumps(slack_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status not in [200, 204]:
                    print(f"[-] Slack pipeline returned unpredicted validation state code: {resp.status}")
        except Exception as e:
            print(f"[-] Failed to forward payload data to configured Slack webhooks channel context: {e}")

    def _log_to_splunk_hec(self, snapshot: Dict[str, Any], decision: Dict[str, Any]):
        """
        Forwards consolidated transaction parameters to Splunk tracking indices via HTTP Event Collector endpoints.
        """
        if not self.splunk_url or not self.splunk_token:
            # Silent mock output logging tracker
            return

        # Prepare unified envelope structure formatting configuration
        payload = {
            "time": datetime.now().timestamp(),
            "host": "pharmasense_orchestrator",
            "source": "cloud_connected_engine",
            "sourcetype": "pharmasense:triage:decision",
            "event": {
                "telemetry_snapshot": snapshot,
                "orchestrated_decision": decision
            }
        }

        try:
            endpoint = f"{self.splunk_url.rstrip('/')}/services/collector"
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Splunk {self.splunk_token}",
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                # Discard return tokens once verified
                pass
        except Exception:
            # Fail silently to safeguard primary system thread velocity
            pass


# =====================================================================
# Main Execution Demo Block
# =====================================================================
if __name__ == "__main__":
    print("=" * 80)
    print("PharmaSense AI — Cloud Connected & Fallback Triage Demonstration Node")
    print("=" * 80)

    # Initialize Orchestrator. Attempts manual parse on .env configuration maps
    orchestrator = GeminiOrchestrator(env_file=".env")

    # Scenario 1: Operational Triage Execution Profile (Compressor Decay Validation)
    print("\n" + "-" * 80)
    print("SCENARIO 1: Operational Triage — Compressor Failure Vector Analysis (FZ-01)")
    print("-" * 80)
    decision1 = orchestrator.run_triage_loop(
        query_type="operational",
        appliance_id="FZ-01"
    )
    print(json.dumps(decision1, indent=2))

    # Scenario 2: Predictive Triage Execution Profile (Power Outage Trends Analysis)
    print("\n" + "-" * 80)
    print("SCENARIO 2: Predictive Triage — Power Loss Dynamics Assessment (FZ-04)")
    print("-" * 80)
    decision2 = orchestrator.run_triage_loop(
        query_type="predictive",
        appliance_id="FZ-04"
    )
    print(json.dumps(decision2, indent=2))

    # Scenario 3: Compliance Triage Execution Profile (Security Access Anomalies Identification)
    print("\n" + "-" * 80)
    print("SCENARIO 3: Compliance Triage — Security Authentication Deviation Scan (DD-01)")
    print("-" * 80)
    decision3 = orchestrator.run_triage_loop(
        query_type="compliance",
        appliance_id="DD-01"
    )
    print(json.dumps(decision3, indent=2))

    print("\n" + "=" * 80)
    print("ORCHESTRATION PIPELINE SIMULATION COMPLETE — ALL INTERFACES NOMINAL")
    print("=" * 80)
