#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PharmaSense AI - Offline Decision Trees (Gemini API Fallback)

Demonstrates deep decision tree logic for pharmaceutical equipment management
when cloud API is unavailable. Matches Gemini output schema exactly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import json
from datetime import datetime
from pharma_sense_ai import mock_db, triage, decide_fleet


def format_decision_output(decision: dict, indent: int = 2) -> str:
    """Pretty-print a decision dictionary."""
    indent_str = " " * indent
    output = []
    
    output.append(f"{indent_str}Decision ID: {decision['decision_id']}")
    output.append(f"{indent_str}Risk Level: {decision['risk_level']}")
    output.append(f"{indent_str}Severity: {decision['severity']:.1%}")
    output.append(f"{indent_str}Recoverable: {decision['recoverable']}")
    output.append(f"{indent_str}Requires Approval: {decision['requires_human_approval']}")
    
    if decision['approval_message']:
        output.append(f"{indent_str}Approval Message: {decision['approval_message']}")
    
    output.append(f"{indent_str}Analysis: {decision['analysis']}")
    
    if decision['action_plan']:
        output.append(f"{indent_str}Action Plan:")
        for i, action in enumerate(decision['action_plan'], 1):
            output.append(f"{indent_str}  {i}. [{action['channel']}] {action['action']}")
            for key, value in action.get('params', {}).items():
                output.append(f"{indent_str}     - {key}: {value}")
    
    return "\n".join(output)


def example_1_freezer_decisions():
    """Demonstrate offline decision trees for PharmaFreezer."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: PharmaFreezer Offline Decisions")
    print("=" * 80)
    
    db = mock_db()
    freezers = db["pharma_freezers"]
    
    # Simulate 10 hours to trigger various failure modes
    for _ in range(20):
        for fz in freezers:
            fz.step(0.5)
    
    print("\nGenerating offline decisions for all freezers:")
    print("-" * 80)
    
    for fz in freezers:
        snapshot = fz.snapshot(datetime.now())
        decision = triage(snapshot)
        
        print(f"\n{fz.equipment_id} ({fz.profile}):")
        print(format_decision_output(decision))


def example_2_dispenser_decisions():
    """Demonstrate offline decision trees for DrugDispenser."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: DrugDispenser Offline Decisions")
    print("=" * 80)
    
    db = mock_db()
    dispensers = db["drug_dispensers"]
    
    # Simulate 5 hours
    for _ in range(10):
        for dd in dispensers:
            dd.step(0.5)
    
    print("\nGenerating offline decisions for all dispensers:")
    print("-" * 80)
    
    for dd in dispensers:
        snapshot = dd.snapshot(datetime.now())
        decision = triage(snapshot)
        
        print(f"\n{dd.equipment_id} ({dd.profile}):")
        print(format_decision_output(decision))


def example_3_blood_storage_decisions():
    """Demonstrate offline decision trees for BloodStorage."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: BloodStorage Offline Decisions")
    print("=" * 80)
    
    db = mock_db()
    blood_storages = db["blood_storage"]
    
    # Simulate 3 hours
    for _ in range(6):
        for bs in blood_storages:
            bs.step(0.5)
    
    print("\nGenerating offline decisions for all blood storage units:")
    print("-" * 80)
    
    for bs in blood_storages:
        snapshot = bs.snapshot(datetime.now())
        decision = triage(snapshot)
        
        print(f"\n{bs.equipment_id} ({bs.profile}):")
        print(format_decision_output(decision))


def example_4_fleet_coordination():
    """Demonstrate fleet-level decision tree."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Fleet-Level Coordination")
    print("=" * 80)
    
    db = mock_db()
    
    # Simulate 5 hours
    for _ in range(10):
        for category, equipment_list in db.items():
            for equipment in equipment_list:
                equipment.step(0.5)
    
    # Aggregate site metrics
    sites_data = {}
    total_critical = 0
    total_units_at_risk = 0
    
    for category, equipment_list in db.items():
        for equipment in equipment_list:
            site = equipment.site_name
            if site not in sites_data:
                sites_data[site] = {
                    "critical_count": 0,
                    "equipment": []
                }
            
            snapshot = equipment.snapshot(datetime.now())
            prediction = {
                "status": snapshot.get("status", "UNKNOWN"),
                "risk": "CRITICAL" if snapshot.get("status", "UNKNOWN") in 
                        ["POWER_LOSS", "COMPRESSOR_FAIL", "TEMP_EXCURSION"] else "OK"
            }
            
            sites_data[site]["equipment"].append({
                "id": equipment.equipment_id,
                "type": category.rstrip('s'),
                "status": snapshot.get("status"),
            })
            
            if prediction["risk"] == "CRITICAL":
                sites_data[site]["critical_count"] += 1
                total_critical += 1
            
            if category == "blood_storage":
                total_units_at_risk += snapshot.get("units_total", 0)
    
    # Generate fleet decision
    fleet_metrics = {
        "sites": sites_data,
        "total_equipment": sum(
            len(equip_list) for equip_list in db.values()
        ),
        "total_critical": total_critical,
        "total_units_at_risk": total_units_at_risk,
    }
    
    fleet_decision = decide_fleet(fleet_metrics)
    
    print("\nFleet Status Summary:")
    print("-" * 80)
    print(f"Total Equipment: {fleet_metrics['total_equipment']}")
    print(f"Total Critical: {fleet_metrics['total_critical']}")
    print(f"Total Units at Risk: {fleet_metrics['total_units_at_risk']}")
    print(f"\nSite Breakdown:")
    for site_name, site_data in sites_data.items():
        print(f"  {site_name}: {len(site_data['equipment'])} units, "
              f"{site_data['critical_count']} critical")
    
    print("\nFleet Decision:")
    print(format_decision_output(fleet_decision))


def example_5_critical_escalation_scenarios():
    """Demonstrate escalation logic for various critical scenarios."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Critical Escalation Scenarios")
    print("=" * 80)
    
    scenarios = [
        {
            "name": "Temperature Excursion (Freezer)",
            "equipment_type": "PharmaFreezer",
            "temp_c": 15.0,
            "power_ok": True,
            "compressor_ok": True,
            "equipment_id": "FZ-SCENARIO-1"
        },
        {
            "name": "Power Loss (Freezer)",
            "equipment_type": "PharmaFreezer",
            "temp_c": -20.0,
            "power_ok": False,
            "compressor_ok": True,
            "equipment_id": "FZ-SCENARIO-2"
        },
        {
            "name": "Access Anomaly (Dispenser)",
            "equipment_type": "DrugDispenser",
            "temp_c": 20.0,
            "motor_ok": True,
            "unusual_access": True,
            "access_count_24h": 75,
            "equipment_id": "DD-SCENARIO-1"
        },
        {
            "name": "Blood Freezing (Blood Storage)",
            "equipment_type": "BloodStorage",
            "temp_c": -0.5,
            "units_total": 200,
            "equipment_id": "BS-SCENARIO-1"
        },
        {
            "name": "Blood Contamination (Blood Storage)",
            "equipment_type": "BloodStorage",
            "temp_c": 7.5,
            "units_total": 200,
            "equipment_id": "BS-SCENARIO-2"
        },
    ]
    
    print("\nCritical Scenario Decisions:")
    print("-" * 80)
    
    for scenario in scenarios:
        # Merge with defaults
        data = {
            "temp_c": 20.0,
            "humidity_pct": 45.0,
            "power_ok": True,
            "compressor_ok": True,
            "door_seal_ok": True,
            "temp_sensor_ok": True,
            "motor_ok": True,
            "inventory_pct": 50.0,
            "unusual_access": False,
            "access_count_24h": 12,
            "units_total": 200,
            "units_expiring_48h": 10,
            "contamination_risk_pct": 2.0,
            "co2_ppm": 400.0,
            "status": "NOMINAL",
        }
        data.update(scenario)
        
        decision = triage(data)
        
        print(f"\nScenario: {scenario['name']}")
        print(f"Decision: {decision['decision_id']}")
        print(f"Risk Level: {decision['risk_level']} (Severity: {decision['severity']:.0%})")
        print(f"Requires Approval: {decision['requires_human_approval']}")
        print(f"Analysis: {decision['analysis'][:120]}...")
        if decision['approval_message']:
            print(f"Message: {decision['approval_message']}")


def example_6_schema_validation():
    """Demonstrate that all decisions match the required schema."""
    print("\n" + "=" * 80)
    print("EXAMPLE 6: Schema Validation")
    print("=" * 80)
    
    db = mock_db()
    
    # Required schema fields
    required_fields = [
        "decision_id",
        "analysis",
        "severity",
        "risk_level",
        "recoverable",
        "requires_human_approval",
        "approval_message",
        "action_plan"
    ]
    
    required_action_fields = ["channel", "action", "params"]
    
    print("\nValidating decision schema across all equipment:")
    print("-" * 80)
    
    total_decisions = 0
    total_valid = 0
    
    for category, equipment_list in db.items():
        for equipment in equipment_list:
            # Step equipment
            equipment.step(1.0)
            snapshot = equipment.snapshot(datetime.now())
            decision = triage(snapshot)
            
            total_decisions += 1
            valid = True
            
            # Check required fields
            for field in required_fields:
                if field not in decision:
                    print(f"  FAIL: {equipment.equipment_id} - Missing field: {field}")
                    valid = False
            
            # Validate field types
            if not isinstance(decision.get("severity"), (int, float)):
                print(f"  FAIL: {equipment.equipment_id} - severity must be numeric")
                valid = False
            
            if decision.get("risk_level") not in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
                print(f"  FAIL: {equipment.equipment_id} - invalid risk_level")
                valid = False
            
            # Validate action_plan structure
            for action in decision.get("action_plan", []):
                for req_field in required_action_fields:
                    if req_field not in action:
                        print(f"  FAIL: {equipment.equipment_id} - action missing {req_field}")
                        valid = False
            
            # Check CRITICAL consistency
            if decision.get("risk_level") == "CRITICAL":
                if not decision.get("requires_human_approval"):
                    print(f"  FAIL: {equipment.equipment_id} - CRITICAL must require approval")
                    valid = False
            
            if valid:
                total_valid += 1
    
    print(f"\nSchema Validation Results:")
    print(f"  Total Decisions: {total_decisions}")
    print(f"  Valid: {total_valid}/{total_decisions}")
    print(f"  Pass Rate: {total_valid/total_decisions*100:.0f}%")
    
    if total_valid == total_decisions:
        print("\n  [PASS] All decisions conform to schema")
    else:
        print(f"\n  [FAIL] {total_decisions - total_valid} decisions have schema errors")


def example_7_json_export():
    """Export decisions as JSON for integration."""
    print("\n" + "=" * 80)
    print("EXAMPLE 7: JSON Export for Integration")
    print("=" * 80)
    
    db = mock_db()
    
    # Collect decisions
    decisions = []
    for category, equipment_list in db.items():
        for equipment in equipment_list:
            equipment.step(2.0)
            snapshot = equipment.snapshot(datetime.now())
            decision = triage(snapshot)
            
            # Add equipment context
            decision["equipment_id"] = equipment.equipment_id
            decision["equipment_type"] = equipment.__class__.__name__
            decision["timestamp"] = datetime.now().isoformat()
            
            decisions.append(decision)
    
    print("\nJSON Export Sample (critical decisions only):")
    print("-" * 80)
    
    critical_decisions = [d for d in decisions if d["risk_level"] == "CRITICAL"]
    
    for decision in critical_decisions[:2]:  # Show first 2
        json_str = json.dumps(decision, indent=2)
        print(f"\n{decision['equipment_id']}:")
        print(json_str[:500] + "...")  # Truncate for readability


def main():
    """Run all offline decision tree examples."""
    print("\n" + "=" * 80)
    print("PharmaSense AI — Offline Decision Trees (Gemini API Fallback)")
    print("=" * 80)
    
    example_1_freezer_decisions()
    example_2_dispenser_decisions()
    example_3_blood_storage_decisions()
    example_4_fleet_coordination()
    example_5_critical_escalation_scenarios()
    example_6_schema_validation()
    example_7_json_export()
    
    print("\n" + "=" * 80)
    print("ALL DECISION TREE EXAMPLES COMPLETED")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
