#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PharmaSense AI — Splunk HEC Telemetry Sender
Sends pharmaceutical equipment telemetry and decisions to Splunk HTTP Event Collector.

Uses urllib only (no external dependencies).

Licensed under the Apache License, Version 2.0
You may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
import ssl
from typing import Dict, Any, List, Optional


class SplunkHECClient:
    """
    Sends pharmaceutical equipment telemetry to Splunk HTTP Event Collector.
    
    Features:
    - Telemetry events with decision enrichment
    - Batch event submission
    - Alert/notable event generation
    - Mock mode when HEC not configured
    - Automatic retry on failure
    - SSL verification control
    """
    
    def __init__(self, hec_url: Optional[str] = None, hec_token: Optional[str] = None):
        """
        Initialize Splunk HEC client.
        
        Args:
            hec_url: Splunk HEC URL (e.g., https://splunk.example.com:8088)
                    If None, loads from SPLUNK_HEC_URL environment variable
            hec_token: HEC authentication token
                      If None, loads from SPLUNK_HEC_TOKEN environment variable
        """
        self.hec_url = hec_url or os.getenv("SPLUNK_HEC_URL", "")
        self.hec_token = hec_token or os.getenv("SPLUNK_HEC_TOKEN", "")
        self.mock_mode = not (self.hec_url and self.hec_token)
        
        if self.mock_mode:
            print("[SplunkHECClient] MOCK MODE - Events will print to stdout")
            print("[SplunkHECClient] Configure SPLUNK_HEC_URL and SPLUNK_HEC_TOKEN for production")
        else:
            print(f"[SplunkHECClient] Connected to {self.hec_url}")
        
        self.event_count = 0
        self.batch_count = 0
        self.alert_count = 0
    
    def send_event(self, appliance_snapshot: Dict[str, Any], 
                  decision: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send a single appliance telemetry event to Splunk.
        
        Args:
            appliance_snapshot: Equipment telemetry snapshot
            decision: Optional decision object with risk_level, severity, etc.
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not appliance_snapshot:
            return False
        
        # Build event with appliance data
        event_data = dict(appliance_snapshot)
        
        # Enrich with decision data if provided
        if decision:
            event_data['risk_level'] = decision.get('risk_level', 'UNKNOWN')
            event_data['severity'] = decision.get('severity', 0.0)
            event_data['decision_id'] = decision.get('decision_id', 'N/A')
            event_data['requires_human_approval'] = decision.get('requires_human_approval', False)
            
            # Extract first action if available
            if decision.get('action_plan'):
                first_action = decision['action_plan'][0]
                event_data['recommended_action'] = first_action.get('action', 'N/A')
                event_data['action_channel'] = first_action.get('channel', 'N/A')
        
        # Build HEC payload
        payload = {
            "time": int(time.time()),
            "index": "pharmasense",
            "source": "pharmasense:simulation",
            "sourcetype": "pharma:telemetry",
            "event": event_data
        }
        
        return self._post_event(payload, retry=True)
    
    def send_batch(self, events: List[Dict[str, Any]], max_batch: int = 100) -> bool:
        """
        Send multiple events in a batch HEC request (newline-separated JSON).
        
        Args:
            events: List of event dictionaries
            max_batch: Maximum events per batch (default 100)
        
        Returns:
            True if all batches sent successfully
        """
        if not events:
            return False
        
        all_success = True
        
        # Process in chunks
        for i in range(0, len(events), max_batch):
            batch = events[i:i+max_batch]
            
            # Build newline-separated JSON
            batch_lines = []
            for event in batch:
                if isinstance(event, dict):
                    payload = {
                        "time": int(time.time()),
                        "index": "pharmasense",
                        "source": "pharmasense:batch",
                        "sourcetype": "pharma:telemetry",
                        "event": event
                    }
                    batch_lines.append(json.dumps(payload))
            
            if batch_lines:
                batch_data = "\n".join(batch_lines)
                success = self._post_batch(batch_data)
                all_success = all_success and success
        
        return all_success
    
    def send_alert(self, alert_type: str, message: str, 
                  severity: str = "MEDIUM", appliance_id: str = "UNKNOWN") -> bool:
        """
        Send an alert/notable event to Splunk.
        
        Args:
            alert_type: Type of alert (e.g., "EQUIPMENT_FAILURE", "ACCESS_ANOMALY")
            message: Alert message
            severity: Severity level (CRITICAL, HIGH, MEDIUM, LOW)
            appliance_id: Equipment ID
        
        Returns:
            True if sent successfully
        """
        alert_data = {
            "alert_type": alert_type,
            "message": message,
            "severity": severity,
            "appliance_id": appliance_id,
            "timestamp": int(time.time())
        }
        
        payload = {
            "time": int(time.time()),
            "index": "pharmasense",
            "source": "pharmasense:alerts",
            "sourcetype": "pharma:alert",
            "event": alert_data
        }
        
        return self._post_event(payload, retry=True)
    
    def _post_event(self, payload: Dict[str, Any], retry: bool = True) -> bool:
        """
        POST a single event to Splunk HEC.
        
        Args:
            payload: HEC event payload
            retry: Whether to retry once on failure
        
        Returns:
            True if successful
        """
        if self.mock_mode:
            print(f"[MOCK HEC] Event: {json.dumps(payload, indent=2)}")
            self.event_count += 1
            return True
        
        try:
            # Create request
            url = f"{self.hec_url}/services/collector"
            headers = {
                "Authorization": f"Splunk {self.hec_token}",
                "Content-Type": "application/json"
            }
            
            request_data = json.dumps(payload).encode('utf-8')
            request = urllib.request.Request(
                url,
                data=request_data,
                headers=headers,
                method='POST'
            )
            
            # Create SSL context (skip verification for local dev)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Send request
            with urllib.request.urlopen(request, context=ssl_context, timeout=10) as response:
                result = response.read().decode('utf-8')
                
                # Check for success
                if 'Success' in result or response.status in (200, 201):
                    self.event_count += 1
                    return True
        
        except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
            error_msg = f"{type(e).__name__}: {str(e)[:100]}"
            
            # Retry once on failure
            if retry:
                print(f"[SplunkHECClient] Send failed ({error_msg}), retrying...")
                time.sleep(1)  # Brief delay before retry
                return self._post_event(payload, retry=False)
            else:
                print(f"[SplunkHECClient] Send failed after retry: {error_msg}")
                return False
        
        return False
    
    def _post_batch(self, batch_data: str) -> bool:
        """
        POST a batch of newline-separated JSON events to Splunk HEC.
        
        Args:
            batch_data: Newline-separated JSON events
        
        Returns:
            True if successful
        """
        if self.mock_mode:
            lines = batch_data.split('\n')
            print(f"[MOCK HEC] Batch: {len(lines)} events")
            for line in lines[:3]:  # Show first 3
                print(f"  {line[:100]}...")
            if len(lines) > 3:
                print(f"  ... and {len(lines) - 3} more")
            self.batch_count += 1
            return True
        
        try:
            url = f"{self.hec_url}/services/collector"
            headers = {
                "Authorization": f"Splunk {self.hec_token}",
                "Content-Type": "application/json"
            }
            
            request_data = batch_data.encode('utf-8')
            request = urllib.request.Request(
                url,
                data=request_data,
                headers=headers,
                method='POST'
            )
            
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(request, context=ssl_context, timeout=30) as response:
                result = response.read().decode('utf-8')
                
                if 'Success' in result or response.status in (200, 201):
                    self.batch_count += 1
                    return True
        
        except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
            print(f"[SplunkHECClient] Batch send failed: {type(e).__name__}")
            return False
        
        return False
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics on sent events."""
        return {
            "events_sent": self.event_count,
            "batches_sent": self.batch_count,
            "alerts_sent": self.alert_count,
            "mock_mode": self.mock_mode
        }


def main():
    """
    Demonstrate SplunkHECClient with mock mode and example scenarios.
    """
    print("\n" + "=" * 80)
    print("PHARMASENSE AI — SPLUNK HEC TELEMETRY SENDER DEMO")
    print("=" * 80)
    
    # Initialize client (mock mode if no credentials)
    client = SplunkHECClient()
    
    # Scenario 1: Send single telemetry event
    print("\n" + "-" * 80)
    print("SCENARIO 1: Single Telemetry Event")
    print("-" * 80)
    
    appliance_snapshot_1 = {
        "equipment_id": "FZ-01",
        "equipment_type": "PharmaFreezer",
        "site_name": "site_a",
        "status": "COMPRESSOR_FAIL",
        "temp_c": -12.0,
        "humidity_pct": 35.0,
        "power_ok": True,
        "compressor_ok": False,
        "product_count": 500
    }
    
    decision_1 = {
        "decision_id": "DEC-2026-FREEZER-FZ-01",
        "risk_level": "CRITICAL",
        "severity": 0.96,
        "requires_human_approval": True,
        "action_plan": [
            {
                "channel": "MAINTENANCE",
                "action": "EMERGENCY_COMPRESSOR_REPLACEMENT",
                "params": {"priority": "IMMEDIATE"}
            }
        ]
    }
    
    success = client.send_event(appliance_snapshot_1, decision_1)
    print(f"[{'PASS' if success else 'FAIL'}] Single event sent")
    
    # Scenario 2: Send batch of events
    print("\n" + "-" * 80)
    print("SCENARIO 2: Batch Events (5 appliances)")
    print("-" * 80)
    
    batch_events = [
        {
            "equipment_id": "FZ-02",
            "equipment_type": "PharmaFreezer",
            "site_name": "site_a",
            "status": "DOOR_BREACH",
            "temp_c": -20.0,
            "humidity_pct": 85.0
        },
        {
            "equipment_id": "DD-01",
            "equipment_type": "DrugDispenser",
            "site_name": "site_a",
            "status": "ACCESS_ANOMALY",
            "temp_c": 20.0,
            "inventory_pct": 75.0,
            "access_count_24h": 55
        },
        {
            "equipment_id": "BS-01",
            "equipment_type": "BloodStorage",
            "site_name": "site_b",
            "status": "TEMP_EXCURSION",
            "temp_c": 6.5,
            "units_total": 200,
            "contamination_risk_pct": 25.0
        },
        {
            "equipment_id": "FZ-04",
            "equipment_type": "PharmaFreezer",
            "site_name": "site_b",
            "status": "POWER_LOSS",
            "temp_c": -18.0,
            "power_ok": False
        },
        {
            "equipment_id": "DD-02",
            "equipment_type": "DrugDispenser",
            "site_name": "site_c",
            "status": "INVENTORY_LOW",
            "temp_c": 20.0,
            "inventory_pct": 5.0
        }
    ]
    
    success = client.send_batch(batch_events)
    print(f"[{'PASS' if success else 'FAIL'}] Batch of {len(batch_events)} events sent")
    
    # Scenario 3: Send alerts
    print("\n" + "-" * 80)
    print("SCENARIO 3: Notable Events/Alerts")
    print("-" * 80)
    
    alerts = [
        ("EQUIPMENT_FAILURE", "Compressor failure on FZ-01 - immediate action required", "CRITICAL", "FZ-01"),
        ("ACCESS_ANOMALY", "Unusual access pattern detected on DD-01", "HIGH", "DD-01"),
        ("TEMP_EXCURSION", "Blood storage temperature exceeded safety threshold", "CRITICAL", "BS-01"),
    ]
    
    for alert_type, message, severity, appliance_id in alerts:
        success = client.send_alert(alert_type, message, severity, appliance_id)
        print(f"[{'PASS' if success else 'FAIL'}] Alert: {alert_type} ({severity})")
    
    # Scenario 4: Enriched events with decisions
    print("\n" + "-" * 80)
    print("SCENARIO 4: Enriched Telemetry (Snapshot + Decision)")
    print("-" * 80)
    
    enriched_snapshots = [
        {
            "snapshot": {
                "equipment_id": "BS-02",
                "equipment_type": "BloodStorage",
                "site_name": "site_b",
                "status": "EXPIRY_ALERT",
                "temp_c": 4.0,
                "units_total": 200,
                "units_expiring_48h": 15
            },
            "decision": {
                "decision_id": "DEC-2026-BS-02",
                "risk_level": "HIGH",
                "severity": 0.60,
                "requires_human_approval": False,
                "action_plan": [
                    {
                        "channel": "COMPLIANCE",
                        "action": "ALERT_BLOOD_BANK_COORDINATOR",
                        "params": {"units_affected": 15}
                    }
                ]
            }
        }
    ]
    
    for item in enriched_snapshots:
        success = client.send_event(item['snapshot'], item['decision'])
        print(f"[{'PASS' if success else 'FAIL'}] Enriched event: {item['snapshot']['equipment_id']}")
    
    # Summary
    print("\n" + "=" * 80)
    print("DEMO SUMMARY")
    print("=" * 80)
    
    stats = client.get_stats()
    print(f"\nEvents sent: {stats['events_sent']}")
    print(f"Batches sent: {stats['batches_sent']}")
    print(f"Mode: {'MOCK' if stats['mock_mode'] else 'PRODUCTION'}")
    
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
