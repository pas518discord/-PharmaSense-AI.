#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PharmaSense AI — Gemini Orchestrator
Cloud-connected decision orchestration with offline fallback.

Queries SplunkMCPServer for telemetry context, sends enriched data to Gemini API,
and posts human-in-the-loop alerts to Slack for critical events.

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
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, Any, Optional
from pharma_sense_ai import mock_db, triage as offline_triage, predict_failure


def _is_placeholder_url(value: str) -> bool:
    """Return True for example values copied from .env templates."""
    placeholders = ("YOUR/", "WEBHOOK", "T00000000", "XXXXXXXXXXXXXXXX")
    return any(marker in value for marker in placeholders)


class GeminiOrchestrator:
    """
    Orchestrates pharmaceutical equipment decision-making via Gemini API
    with automatic fallback to offline decision trees when API unavailable.
    """
    
    def __init__(self, env_file: str = ".env"):
        """
        Initialize orchestrator by loading API keys from environment.
        
        Args:
            env_file: Path to .env file (optional, checks env vars first)
        """
        # Load from .env file if it exists
        if os.path.exists(env_file):
            self._load_env_file(env_file)
        
        # Get from environment
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
        self.splunk_mcp_url = os.getenv("SPLUNK_MCP_URL", "http://localhost:5000")
        if _is_placeholder_url(self.slack_webhook_url):
            self.slack_webhook_url = ""
        
        self.gemini_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        self.fleet_db = None
        self.call_history = []
        
        print(f"[GeminiOrchestrator] Initialized")
        print(f"  Gemini API: {'CONFIGURED' if self.gemini_api_key else 'NOT CONFIGURED (fallback enabled)'}")
        print(f"  Slack Webhook: {'CONFIGURED' if self.slack_webhook_url else 'NOT CONFIGURED (HITL disabled)'}")
        print(f"  Splunk MCP: {self.splunk_mcp_url}")
    
    @staticmethod
    def _load_env_file(env_file: str) -> None:
        """Load environment variables from .env file."""
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip().strip('"\'')
        except FileNotFoundError:
            pass  # .env file optional
    
    def _query_splunk_mcp(self, appliance_id: Optional[str] = None, 
                         site_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Query SplunkMCPServer for appliance telemetry context.
        
        In production, this would query actual Splunk MCP server.
        For demo, we use mock_db() from pharma_sense_ai.
        """
        if self.fleet_db is None:
            self.fleet_db = mock_db()
        
        # Collect telemetry from all equipment
        telemetry = []
        for category, equipment_list in self.fleet_db.items():
            for equipment in equipment_list:
                # Match on appliance_id or site_id if specified
                if appliance_id and equipment.equipment_id != appliance_id:
                    continue
                if site_id and equipment.site_name != site_id:
                    continue
                
                snapshot = equipment.snapshot(datetime.now())
                prediction = predict_failure(snapshot)
                
                telemetry.append({
                    "appliance": snapshot,
                    "prediction": prediction,
                    "status_label": equipment.status_label()
                })
        
        return {
            "timestamp": datetime.now().isoformat(),
            "telemetry": telemetry,
            "appliance_id": appliance_id,
            "site_id": site_id
        }
    
    def query_gemini(self, system_instruction: str, prompt: str, 
                    context_data: Dict[str, Any], query_type: str) -> Dict[str, Any]:
        """
        Query Gemini 1.5 Flash API with pharmaceutical context.
        Falls back to offline decision trees on API failure.
        
        Args:
            system_instruction: System prompt for Gemini
            prompt: User prompt with specific query
            context_data: Telemetry and prediction context
            query_type: Type of query (operational, predictive, compliance)
        
        Returns:
            Decision dictionary matching pharma_sense_ai schema
        """
        if not self.gemini_api_key:
            print(f"[GeminiOrchestrator] No Gemini API key - using offline fallback")
            return self._offline_decision(context_data)
        
        try:
            # Build Gemini API request
            request_body = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {"text": system_instruction},
                            {"text": f"\n\nContext:\n{json.dumps(context_data, indent=2)}"},
                            {"text": f"\n\nQuery:\n{prompt}"}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "responseMimeType": "application/json"
                }
            }
            
            # Make HTTPS request
            url = f"{self.gemini_endpoint}?key={self.gemini_api_key}"
            headers = {"Content-Type": "application/json"}
            
            request = urllib.request.Request(
                url,
                data=json.dumps(request_body).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            
            with urllib.request.urlopen(request, timeout=30) as response:
                response_data = json.loads(response.read().decode('utf-8'))
            
            # Extract decision from Gemini response
            if 'candidates' in response_data and response_data['candidates']:
                candidate = response_data['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    text_part = candidate['content']['parts'][0].get('text', '{}')
                    decision = json.loads(text_part)
                    
                    # Ensure decision has required fields
                    decision = self._normalize_decision(decision, context_data)
                    
                    print(f"[Gemini] Decision: {decision.get('risk_level')} - "
                          f"{decision.get('analysis', '')[:80]}")
                    return decision
        
        except (urllib.error.URLError, urllib.error.HTTPError, 
                json.JSONDecodeError, KeyError, Exception) as e:
            print(f"[GeminiOrchestrator] Gemini API error: {type(e).__name__}: {str(e)[:100]}")
        
        # Fallback to offline decision trees
        print(f"[GeminiOrchestrator] Falling back to offline decision trees")
        return self._offline_decision(context_data)
    
    def _offline_decision(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate decision using offline decision trees."""
        telemetry = context_data.get('telemetry', [])
        
        if not telemetry:
            return {
                "decision_id": "DEC-FALLBACK-NODATA",
                "analysis": "No telemetry available for analysis",
                "severity": 0.0,
                "risk_level": "LOW",
                "recoverable": True,
                "requires_human_approval": False,
                "approval_message": None,
                "action_plan": []
            }
        
        # Use first appliance's data
        appliance_snapshot = telemetry[0]['appliance']
        return offline_triage(appliance_snapshot)
    
    @staticmethod
    def _normalize_decision(decision: Dict[str, Any], 
                           context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure decision has all required fields matching our schema.
        """
        required_fields = {
            'decision_id': f"DEC-GEMINI-{context_data.get('appliance_id', 'UNKNOWN')}",
            'analysis': 'Analysis pending',
            'severity': 0.5,
            'risk_level': 'MEDIUM',
            'recoverable': True,
            'requires_human_approval': False,
            'approval_message': None,
            'action_plan': []
        }
        
        for key, default_value in required_fields.items():
            if key not in decision:
                decision[key] = default_value
        
        return decision
    
    def send_hitl_alert(self, decision: Dict[str, Any], 
                       appliance_data: Dict[str, Any]) -> bool:
        """
        Post human-in-the-loop alert to Slack webhook for CRITICAL events.
        
        Args:
            decision: Decision dictionary
            appliance_data: Appliance telemetry snapshot
        
        Returns:
            True if alert sent successfully
        """
        if not self.slack_webhook_url:
            print(f"[GeminiOrchestrator] Slack webhook not configured - HITL alert not sent")
            return False
        
        risk_level = decision.get('risk_level', 'MEDIUM')
        if risk_level not in ['CRITICAL', 'HIGH']:
            return False  # Only alert on CRITICAL and HIGH
        
        # Determine color
        color = "#d62728" if risk_level == "CRITICAL" else "#ff7f0e"
        
        appliance_id = appliance_data.get('equipment_id', 'UNKNOWN')
        
        # Build Slack message
        slack_payload = {
            "attachments": [
                {
                    "fallback": f"PharmaSense Alert: {appliance_id} {risk_level}",
                    "color": color,
                    "title": f"🚨 PharmaSense Alert — {appliance_id}",
                    "title_link": f"https://pharmasense.local/appliances/{appliance_id}",
                    "fields": [
                        {
                            "title": "Risk Level",
                            "value": risk_level,
                            "short": True
                        },
                        {
                            "title": "Severity",
                            "value": f"{decision.get('severity', 0):.0%}",
                            "short": True
                        },
                        {
                            "title": "Equipment",
                            "value": f"{appliance_data.get('equipment_type', 'Unknown')} "
                                    f"({appliance_data.get('site_name', 'Unknown')})",
                            "short": True
                        },
                        {
                            "title": "Status",
                            "value": appliance_data.get('status', 'UNKNOWN'),
                            "short": True
                        },
                        {
                            "title": "Analysis",
                            "value": decision.get('analysis', 'No analysis'),
                            "short": False
                        }
                    ],
                    "actions": [
                        {
                            "type": "button",
                            "text": "Approve Action",
                            "url": f"https://pharmasense.local/approve/{decision.get('decision_id', 'unknown')}"
                        },
                        {
                            "type": "button",
                            "text": "Override — Keep Running",
                            "url": f"https://pharmasense.local/override/{decision.get('decision_id', 'unknown')}"
                        }
                    ],
                    "footer": "PharmaSense AI",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
        
        try:
            request = urllib.request.Request(
                self.slack_webhook_url,
                data=json.dumps(slack_payload).encode('utf-8'),
                headers={"Content-Type": "application/json"},
                method='POST'
            )
            
            with urllib.request.urlopen(request, timeout=10) as response:
                result = response.read().decode('utf-8')
                print(f"[Slack] Alert sent for {appliance_id}: {result}")
                return result == "ok"
        
        except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
            print(f"[GeminiOrchestrator] Slack alert failed: {type(e).__name__}")
            return False
    
    def run_triage_loop(self, query_type: str = "operational", 
                       appliance_id: Optional[str] = None,
                       site_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Main triage loop: collect telemetry, query Gemini, post alerts.
        
        Args:
            query_type: Type of query (operational, predictive, compliance)
            appliance_id: Specific appliance to analyze
            site_id: Specific site to analyze
        
        Returns:
            Decision dictionary
        """
        print(f"\n[GeminiOrchestrator] Running {query_type} triage loop")
        print(f"  Appliance: {appliance_id or 'all'}, Site: {site_id or 'all'}")
        
        # Step 1: Query Splunk MCP for telemetry
        print(f"[Step 1] Querying Splunk MCP for telemetry context...")
        context_data = self._query_splunk_mcp(appliance_id, site_id)
        
        if not context_data.get('telemetry'):
            print(f"  [FAIL] No telemetry available")
            return {"risk_level": "LOW", "analysis": "No data"}
        
        print(f"  [PASS] Retrieved {len(context_data['telemetry'])} telemetry records")
        
        # Step 2: Build system instruction
        print(f"[Step 2] Building Gemini prompt...")
        system_instruction = """You are PharmaSense, an AI assistant monitoring pharmaceutical 
cold chain equipment. Analyze the provided telemetry data and generate a JSON action plan.

Your response MUST be valid JSON with these fields:
{
  "decision_id": "DEC-GEMINI-{appliance_id}",
  "analysis": "Detailed analysis of the situation",
  "severity": 0.0-1.0,
  "risk_level": "CRITICAL|HIGH|MEDIUM|LOW",
  "recoverable": true/false,
  "requires_human_approval": true/false,
  "approval_message": "Required action if human approval needed",
  "action_plan": [
    {"channel": "SAFETY|MAINTENANCE|COMPLIANCE|NOTIFICATION", "action": "ACTION", "params": {...}}
  ]
}

Consider WHO pharmaceutical storage standards and GxP compliance."""
        
        # Build specific prompt
        telemetry = context_data['telemetry'][0]
        appliance_snapshot = telemetry['appliance']
        prediction = telemetry['prediction']
        
        prompt = f"""Analyze this equipment status:
Equipment: {appliance_snapshot.get('equipment_id')}
Type: {appliance_snapshot.get('equipment_type')}
Status: {appliance_snapshot.get('status')}
Predicted Failure: {prediction.get('predicted_failure')} ({prediction.get('confidence'):.0%} confidence)
Temperature: {appliance_snapshot.get('temp_c')}°C
Query Type: {query_type}

Generate a decision with action plan."""
        
        # Step 3: Query Gemini
        print(f"[Step 3] Querying Gemini 1.5 Flash API...")
        decision = self.query_gemini(system_instruction, prompt, context_data, query_type)
        
        # Step 4: Extract appliance data for alerts
        appliance_data = context_data['telemetry'][0]['appliance']
        
        # Step 5: Post HITL alert if required
        if decision.get('requires_human_approval'):
            print(f"[Step 4] Posting HITL alert to Slack...")
            alert_sent = self.send_hitl_alert(decision, appliance_data)
            print(f"  [{'PASS' if alert_sent else 'SKIP'}] HITL alert {'sent' if alert_sent else 'skipped'}")
        
        # Step 6: Log decision
        print(f"[Step 5] Logging decision...")
        self._log_decision(decision, appliance_data, query_type)
        
        # Step 7: Return decision
        print(f"[Step 6] Triage complete")
        print(f"  Decision ID: {decision.get('decision_id')}")
        print(f"  Risk Level: {decision.get('risk_level')}")
        print(f"  Actions: {len(decision.get('action_plan', []))} items")
        
        return decision
    
    def _log_decision(self, decision: Dict[str, Any], 
                     appliance_data: Dict[str, Any], 
                     query_type: str) -> None:
        """Log decision for audit trail."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "decision_id": decision.get('decision_id'),
            "appliance_id": appliance_data.get('equipment_id'),
            "query_type": query_type,
            "risk_level": decision.get('risk_level'),
            "requires_approval": decision.get('requires_human_approval'),
            "action_count": len(decision.get('action_plan', []))
        }
        
        self.call_history.append(log_entry)
        print(f"  [PASS] Decision logged to audit trail")


def main():
    """
    Demonstrate three triage scenarios:
    1. Operational: Compressor failure detection
    2. Predictive: Power failure trend analysis
    3. Compliance: Access anomaly investigation
    """
    print("\n" + "=" * 80)
    print("PHARMASENSE AI — GEMINI ORCHESTRATOR DEMO")
    print("=" * 80)
    
    # Initialize orchestrator
    orchestrator = GeminiOrchestrator()
    
    # Scenario 1: Operational Triage (Compressor Failure)
    print("\n" + "-" * 80)
    print("SCENARIO 1: Operational Triage — Compressor Failure Detection")
    print("-" * 80)
    
    decision1 = orchestrator.run_triage_loop(
        query_type="operational",
        appliance_id="FZ-01"
    )
    
    # Scenario 2: Predictive Triage (Power Failure Trend)
    print("\n" + "-" * 80)
    print("SCENARIO 2: Predictive Triage — Power Failure Trend Analysis")
    print("-" * 80)
    
    decision2 = orchestrator.run_triage_loop(
        query_type="predictive",
        appliance_id="FZ-04"
    )
    
    # Scenario 3: Compliance Triage (Access Anomaly)
    print("\n" + "-" * 80)
    print("SCENARIO 3: Compliance Triage — Access Anomaly Investigation")
    print("-" * 80)
    
    decision3 = orchestrator.run_triage_loop(
        query_type="compliance",
        appliance_id="DD-01"
    )
    
    # Summary
    print("\n" + "=" * 80)
    print("TRIAGE SUMMARY")
    print("=" * 80)
    print(f"\nScenario 1 (Operational):")
    print(f"  Risk Level: {decision1.get('risk_level')}")
    print(f"  Actions: {len(decision1.get('action_plan', []))}")
    print(f"  Requires Approval: {decision1.get('requires_human_approval')}")
    
    print(f"\nScenario 2 (Predictive):")
    print(f"  Risk Level: {decision2.get('risk_level')}")
    print(f"  Actions: {len(decision2.get('action_plan', []))}")
    print(f"  Requires Approval: {decision2.get('requires_human_approval')}")
    
    print(f"\nScenario 3 (Compliance):")
    print(f"  Risk Level: {decision3.get('risk_level')}")
    print(f"  Actions: {len(decision3.get('action_plan', []))}")
    print(f"  Requires Approval: {decision3.get('requires_human_approval')}")
    
    print(f"\nTotal decisions logged: {len(orchestrator.call_history)}")
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
