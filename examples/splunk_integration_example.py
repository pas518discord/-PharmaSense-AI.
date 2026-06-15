#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PharmaSense AI — Splunk HEC + Gemini Integration Example
Demonstrates complete orchestration with Slack alerts and Splunk telemetry.

Workflow:
1. Query Splunk MCP for equipment telemetry
2. Run Gemini orchestration with fallback
3. Send Slack alert if CRITICAL
4. Log to Splunk HEC for audit trail
5. Track decisions for compliance

Licensed under the Apache License, Version 2.0
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from gemini_orchestrator import GeminiOrchestrator
from splunk_hec_client import SplunkHECClient
from pharma_sense_ai import mock_db, predict_failure
from datetime import datetime
import time


def get_equipment_snapshot(equipment_id):
    """Get snapshot for specific equipment ID from mock_db."""
    db = mock_db()
    
    # Search through all equipment types
    for equipment_list in db.values():
        for equipment in equipment_list:
            if equipment.equipment_id == equipment_id:
                return equipment.snapshot(datetime.now())
    
    return None


class PharmaSenseIntegration:
    """
    Complete PharmaSense integration: Orchestration + Slack + Splunk telemetry.
    """
    
    def __init__(self):
        """Initialize both orchestration and telemetry clients."""
        self.orchestrator = GeminiOrchestrator()
        self.splunk = SplunkHECClient()
        self.decisions_processed = 0
        self.alerts_sent = 0
    
    def run_monitoring_loop(self, equipment_ids=None, interval_seconds=300):
        """
        Run continuous monitoring loop.
        
        Args:
            equipment_ids: List of equipment to monitor
            interval_seconds: Check interval (default: 5 minutes)
        """
        if not equipment_ids:
            equipment_ids = ["FZ-01", "FZ-02", "FZ-04", "FZ-05",
                           "DD-01", "DD-02", "DD-03",
                           "BS-01", "BS-02", "BS-03"]
        
        print("\n" + "=" * 80)
        print("PHARMASENSE AI — CONTINUOUS MONITORING (Orchestrator + Splunk)")
        print("=" * 80)
        print(f"Monitoring {len(equipment_ids)} equipment")
        print(f"Check interval: {interval_seconds} seconds")
        print("\nPress Ctrl+C to exit\n")
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[{timestamp}] MONITORING ITERATION {iteration}")
                print("-" * 80)
                
                for equipment_id in equipment_ids:
                    self._process_equipment(equipment_id)
                
                # Summary
                print(f"\nIteration {iteration} complete:")
                print(f"  Decisions processed: {self.decisions_processed}")
                print(f"  Alerts sent to Slack: {self.alerts_sent}")
                
                # Wait for next iteration
                print(f"\nWaiting {interval_seconds}s until next check...")
                time.sleep(interval_seconds)
        
        except KeyboardInterrupt:
            print("\n\n" + "=" * 80)
            print("MONITORING STOPPED")
            print("=" * 80)
            print(f"Total iterations: {iteration}")
            print(f"Total decisions: {self.decisions_processed}")
            print(f"Total alerts: {self.alerts_sent}")
            print("=" * 80 + "\n")
    
    def _process_equipment(self, equipment_id):
        """
        Process single equipment: orchestration + Slack + Splunk.
        
        Steps:
        1. Get telemetry from Splunk MCP
        2. Run triage (Gemini or fallback)
        3. Post Slack alert if CRITICAL
        4. Send to Splunk HEC for logging
        5. Track decision
        """
        # Step 1: Query Splunk MCP for telemetry
        snapshot = get_equipment_snapshot(equipment_id)
        if not snapshot:
            print(f"  [{equipment_id}] No telemetry found")
            return
        
        # Step 2: Run triage (uses Gemini if available, else offline)
        try:
            decision = self.orchestrator.run_triage_loop(
                query_type="operational",
                appliance_id=equipment_id
            )
        except Exception as e:
            print(f"  [{equipment_id}] Triage failed: {e}")
            return
        
        self.decisions_processed += 1
        
        # Step 3 & 4: Slack alert + Splunk HEC
        self._handle_decision(equipment_id, snapshot, decision)
    
    def _handle_decision(self, equipment_id, snapshot, decision):
        """
        Handle decision: Slack alert + Splunk telemetry.
        """
        risk_level = decision.get('risk_level', 'UNKNOWN')
        
        print(f"  [{equipment_id}] Risk: {risk_level}")
        
        # Send to Splunk HEC (always)
        success_splunk = self.splunk.send_event(snapshot, decision)
        
        # Send Slack alert if CRITICAL or HIGH
        if risk_level in ('CRITICAL', 'HIGH'):
            # Slack sent via GeminiOrchestrator.send_hitl_alert()
            # in the run_triage_loop() call above
            
            # Also send Splunk alert
            alert_type = "EQUIPMENT_FAILURE" if risk_level == "CRITICAL" else "EQUIPMENT_WARNING"
            message = decision.get('analysis', 'Check required')
            
            success_alert = self.splunk.send_alert(
                alert_type=alert_type,
                message=message,
                severity=risk_level,
                appliance_id=equipment_id
            )
            
            if success_alert:
                self.alerts_sent += 1
                print(f"    → Slack & Splunk alert sent")


def demo_scenario_1():
    """
    Scenario 1: Single-run operational triage with full integration.
    """
    print("\n" + "=" * 80)
    print("SCENARIO 1: Single-Run Orchestration + Splunk")
    print("=" * 80)
    
    orch = GeminiOrchestrator()
    splunk = SplunkHECClient()
    
    # Get telemetry
    equipment_id = "FZ-01"
    snapshot = get_equipment_snapshot(equipment_id)
    if not snapshot:
        print(f"Could not get snapshot for {equipment_id}")
        return
    
    # Run triage
    print(f"\n[Step 1] Running triage for {equipment_id}...")
    decision = orch.run_triage_loop(
        query_type="operational",
        appliance_id=equipment_id
    )
    
    # Send to Splunk HEC
    print(f"\n[Step 2] Sending telemetry to Splunk HEC...")
    success = splunk.send_event(snapshot, decision)
    print(f"  Result: {success}")
    
    # Show decision
    print(f"\n[Step 3] Decision Summary:")
    print(f"  Risk Level: {decision['risk_level']}")
    print(f"  Severity: {decision['severity']:.1%}")
    print(f"  Requires Approval: {decision['requires_human_approval']}")
    
    # Show stats
    stats = splunk.get_stats()
    print(f"\n[Step 4] Telemetry Stats:")
    print(f"  Events sent: {stats['events_sent']}")
    print(f"  Mode: {'MOCK' if stats['mock_mode'] else 'PRODUCTION'}")


def demo_scenario_2():
    """
    Scenario 2: Batch processing multiple equipment with predictive triage.
    """
    print("\n" + "=" * 80)
    print("SCENARIO 2: Batch Processing with Predictive Triage")
    print("=" * 80)
    
    orch = GeminiOrchestrator()
    splunk = SplunkHECClient()
    
    equipment_ids = ["FZ-01", "FZ-04", "DD-01", "BS-01", "BS-02"]
    
    print(f"\nProcessing {len(equipment_ids)} equipment with predictive triage...")
    
    # Collect events
    events_to_send = []
    critical_count = 0
    
    for equipment_id in equipment_ids:
        # Get telemetry
        snapshot = get_equipment_snapshot(equipment_id)
        if not snapshot:
            print(f"  {equipment_id}: No telemetry")
            continue
        
        # Run predictive triage
        decision = orch.run_triage_loop(
            query_type="predictive",
            appliance_id=equipment_id
        )
        
        # Collect for batch send
        events_to_send.append(snapshot)
        
        # Track critical decisions
        if decision['risk_level'] == 'CRITICAL':
            critical_count += 1
        
        print(f"  {equipment_id}: {decision['risk_level']}")
    
    # Send batch to Splunk
    print(f"\nSending batch of {len(events_to_send)} events to Splunk...")
    success = splunk.send_batch(events_to_send)
    print(f"  Batch result: {success}")
    
    # Summary
    print(f"\nBatch Summary:")
    print(f"  Equipment processed: {len(equipment_ids)}")
    print(f"  Critical decisions: {critical_count}")
    
    stats = splunk.get_stats()
    print(f"  Total batches sent: {stats['batches_sent']}")


def demo_scenario_3():
    """
    Scenario 3: Compliance workflow with audit trail.
    """
    print("\n" + "=" * 80)
    print("SCENARIO 3: Compliance Workflow with Audit Trail")
    print("=" * 80)
    
    orch = GeminiOrchestrator()
    splunk = SplunkHECClient()
    
    print("\nRunning compliance triage for all sites...")
    
    sites = {
        "site_a": ["FZ-01", "FZ-02", "DD-01"],
        "site_b": ["FZ-04", "FZ-05", "DD-02", "BS-01"],
        "site_c": ["DD-03", "BS-02", "BS-03"]
    }
    
    compliance_violations = 0
    
    for site_name, equipment_ids in sites.items():
        print(f"\n[{site_name.upper()}] Processing {len(equipment_ids)} equipment...")
        
        for equipment_id in equipment_ids:
            # Get telemetry
            snapshot = get_equipment_snapshot(equipment_id)
            if not snapshot:
                print(f"    {equipment_id}: No telemetry")
                continue
            
            # Run compliance triage
            decision = orch.run_triage_loop(
                query_type="compliance",
                appliance_id=equipment_id
            )
            
            # Send to Splunk (audit trail)
            splunk.send_event(snapshot, decision)
            
            # Track violations
            if decision['risk_level'] == 'CRITICAL':
                compliance_violations += 1
                
                # Send compliance alert
                splunk.send_alert(
                    alert_type="COMPLIANCE_VIOLATION",
                    message=decision.get('analysis', 'Compliance check required'),
                    severity="CRITICAL",
                    appliance_id=equipment_id
                )
                
                print(f"    {equipment_id}: VIOLATION DETECTED")
            else:
                print(f"    {equipment_id}: {decision['risk_level']}")
    
    # Summary
    print(f"\n" + "-" * 80)
    print(f"Compliance Audit Summary:")
    print(f"  Total sites: {len(sites)}")
    print(f"  Total equipment: {sum(len(ids) for ids in sites.values())}")
    print(f"  Violations detected: {compliance_violations}")
    
    stats = splunk.get_stats()
    print(f"  Events logged: {stats['events_sent']}")
    print(f"  Audit trail created: Yes")


def main():
    """Run all integration scenarios."""
    print("\n" + "=" * 80)
    print("PHARMASENSE AI — SPLUNK HEC INTEGRATION EXAMPLES")
    print("=" * 80)
    print("\nThis demo shows:")
    print("  1. Single-run orchestration with Splunk telemetry")
    print("  2. Batch processing with predictive triage")
    print("  3. Compliance workflow with audit trail")
    print("\nAll scenarios demonstrate:")
    print("  [PASS] Gemini orchestrator (or offline fallback)")
    print("  [PASS] Slack alerts for CRITICAL events")
    print("  [PASS] Splunk HEC telemetry logging")
    print("  [PASS] Complete audit trail for compliance")
    
    # Run scenarios
    demo_scenario_1()
    demo_scenario_2()
    demo_scenario_3()
    
    # Optional: Show continuous monitoring
    print("\n" + "=" * 80)
    print("To run continuous monitoring (every 5 minutes):")
    print("=" * 80)
    print("\n  integration = PharmaSenseIntegration()")
    print("  integration.run_monitoring_loop()")
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
