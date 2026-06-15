#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import urllib.request
import urllib.error
import ssl

class SplunkHECClient:
    """
    Splunk HTTP Event Collector (HEC) client for PharmaSense AI telemetry.
    Uses standard Python urllib (zero external dependencies).
    """

    def __init__(self):
        # Load credentials from environment variables
        self.hec_url = os.environ.get("SPLUNK_HEC_URL")
        self.hec_token = os.environ.get("SPLUNK_HEC_TOKEN")
        
        # If credentials are missing, seamlessly fallback to mock mode
        self.mock_mode = not (self.hec_url and self.hec_token)
        
        if self.mock_mode:
            print("[SplunkHECClient] Initiating MOCK MODE - Events will stream to stdout")

    def _get_ssl_context(self):
        """Builds a permissive SSL context for local development endpoints."""
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def _post(self, payload_bytes: bytes) -> bool:
        """Core POST dispatcher with automatic 1-retry logic."""
        if self.mock_mode:
            print(f"[MOCK HEC] {payload_bytes.decode('utf-8')}")
            return True

        url = f"{self.hec_url.rstrip('/')}/services/collector"
        headers = {
            "Authorization": f"Splunk {self.hec_token}",
            "Content-Type": "application/json"
        }
        
        req = urllib.request.Request(url, data=payload_bytes, headers=headers, method="POST")

        # Retry once on failure
        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, context=self._get_ssl_context(), timeout=10) as response:
                    if response.getcode() in (200, 201):
                        return True
            except (urllib.error.URLError, urllib.error.HTTPError) as e:
                if attempt == 1:
                    print(f"[-] Splunk HEC delivery failed after retry: {e}")
                    return False
                time.sleep(1) # Brief cooldown before retry
                
        return False

    def send_event(self, appliance_snapshot: dict, decision: dict = None) -> bool:
        """
        Transmits a single telemetry snapshot, enriched with orchestrator decision metrics.
        """
        event_data = appliance_snapshot.copy()

        # Enrich telemetry context with cloud AI decision mapping
        if decision:
            event_data["risk_level"] = decision.get("risk_level")
            event_data["severity"] = decision.get("severity")
            event_data["predicted_failure"] = decision.get("predicted_failure")
            event_data["requires_human_approval"] = decision.get("requires_human_approval")
            
            action_plan = decision.get("action_plan", [])
            if action_plan:
                event_data["recommended_action"] = action_plan[0].get("action")

        payload = {
            "time": int(time.time()),
            "index": "pharmasense",
            "source": "pharmasense:simulation",
            "sourcetype": "pharma:telemetry",
            "event": event_data
        }
        
        return self._post(json.dumps(payload).encode("utf-8"))

    def send_batch(self, events: list) -> bool:
        """
        Transmits multiple telemetry records via newline-separated JSON to maximize 
        network efficiency. Implements safe batch sharding (Max 100/request).
        """
        if not events:
            return False

        max_batch_size = 100
        overall_success = True

        for i in range(0, len(events), max_batch_size):
            chunk = events[i:i + max_batch_size]
            payload_lines = []
            
            for ev in chunk:
                hec_envelope = {
                    "time": int(time.time()),
                    "index": "pharmasense",
                    "source": "pharmasense:simulation",
                    "sourcetype": "pharma:telemetry",
                    "event": ev
                }
                payload_lines.append(json.dumps(hec_envelope))
            
            # Splunk HEC expects newline-separated JSON payloads for bulk transmission
            batch_bytes = "\n".join(payload_lines).encode("utf-8")
            
            if not self._post(batch_bytes):
                overall_success = False
                
        return overall_success

    def send_alert(self, alert_type: str, message: str, severity: str, appliance_id: str) -> bool:
        """
        Dispatches targeted notable alarm events directly to Splunk indices for SOC visibility.
        """
        payload = {
            "time": int(time.time()),
            "index": "pharmasense",
            "source": "pharmasense:alerts",
            "sourcetype": "pharma:alert",
            "event": {
                "alert_type": alert_type,
                "message": message,
                "severity": severity,
                "appliance_id": appliance_id
            }
        }
        
        return self._post(json.dumps(payload).encode("utf-8"))


# ==========================================
# Testing Block (Demonstrating Mock Mode)
# ==========================================
if __name__ == "__main__":
    # In absence of environment variables, this will seamlessly initiate mock logging
    client = SplunkHECClient()
    
    # 1. Dispatching a mock standard event
    sample_snapshot = {"appliance_id": "FZ-01", "temp_c": -12.4, "door_seal_ok": False}
    sample_decision = {
        "risk_level": "CRITICAL",
        "severity": 0.94,
        "requires_human_approval": True,
        "action_plan": [{"action": "EMERGENCY_RESEAL"}]
    }
    client.send_event(sample_snapshot, sample_decision)
    
    # 2. Dispatching a mock critical alert
    client.send_alert("DOOR_BREACH", "Immediate resealing required", "CRITICAL", "FZ-01")