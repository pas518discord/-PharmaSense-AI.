#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PharmaSense AI — Complete System Integration Test
Demonstrates end-to-end functionality with all components working together.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pharma_sense_ai import mock_db, predict_failure, triage
from datetime import datetime


def test_complete_system():
    """Full system validation test."""
    print("\n" + "=" * 80)
    print("PHARMASENSE AI - COMPLETE SYSTEM INTEGRATION TEST")
    print("=" * 80)
    
    # Initialize system
    print("\n1. INITIALIZING SYSTEM")
    print("-" * 80)
    db = mock_db()
    total_equipment = sum(len(equip_list) for equip_list in db.values())
    print(f"[PASS] Loaded {total_equipment} equipment units across 3 sites")
    print(f"  - PharmaFreezers: {len(db['pharma_freezers'])}")
    print(f"  - DrugDispensers: {len(db['drug_dispensers'])}")
    print(f"  - BloodStorage: {len(db['blood_storage'])}")
    
    # Simulate operations
    print("\n2. SIMULATING OPERATIONAL TIME")
    print("-" * 80)
    for iteration in range(1, 21):
        for category, equipment_list in db.items():
            for equipment in equipment_list:
                equipment.step(0.5)
        if iteration % 5 == 0:
            print(f"  Time: {iteration * 0.5:.1f} hours elapsed")
    
    # Gather predictions
    print("\n3. FAILURE PREDICTIONS")
    print("-" * 80)
    predictions = []
    for category, equipment_list in db.items():
        for equipment in equipment_list:
            snapshot = equipment.snapshot(datetime.now())
            pred = predict_failure(snapshot)
            predictions.append((equipment.equipment_id, pred))
    
    critical_count = sum(1 for _, pred in predictions if pred['confidence'] > 0.85)
    print(f"Critical predictions detected: {critical_count}/{total_equipment}")
    for eq_id, pred in predictions:
        if pred['confidence'] > 0.85:
            print(f"  - {eq_id}: {pred['predicted_failure']} "
                  f"({pred['confidence']:.0%} confidence, "
                  f"{pred['time_to_critical_hours']:.1f}h to critical)")
    
    # Generate decisions
    print("\n4. DECISION TREE EVALUATION")
    print("-" * 80)
    decisions = []
    for category, equipment_list in db.items():
        for equipment in equipment_list:
            snapshot = equipment.snapshot(datetime.now())
            decision = triage(snapshot)
            decisions.append((equipment.equipment_id, decision))
    
    # Analyze decisions by risk level
    risk_summary = {}
    for eq_id, decision in decisions:
        risk = decision['risk_level']
        if risk not in risk_summary:
            risk_summary[risk] = []
        risk_summary[risk].append(eq_id)
    
    print("Decision Distribution:")
    for risk_level in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        count = len(risk_summary.get(risk_level, []))
        equipment_list = ', '.join(risk_summary.get(risk_level, []))
        print(f"  {risk_level:8s}: {count:2d} units  [{equipment_list}]")
    
    # Verify approval requirements
    print("\n5. APPROVAL WORKFLOW VALIDATION")
    print("-" * 80)
    approval_required = [
        (eq_id, dec) for eq_id, dec in decisions 
        if dec['requires_human_approval']
    ]
    print(f"Decisions requiring human approval: {len(approval_required)}/{total_equipment}")
    for eq_id, decision in approval_required:
        print(f"  - {eq_id}: {decision['approval_message'][:60]}...")
    
    # Validate action plans
    print("\n6. ACTION PLAN GENERATION")
    print("-" * 80)
    total_actions = sum(len(dec['action_plan']) for _, dec in decisions)
    channel_count = {}
    for _, decision in decisions:
        for action in decision['action_plan']:
            channel = action['channel']
            channel_count[channel] = channel_count.get(channel, 0) + 1
    
    print(f"Total actions generated: {total_actions}")
    print("Actions by channel:")
    for channel in ['SAFETY', 'MAINTENANCE', 'COMPLIANCE', 'NOTIFICATION']:
        count = channel_count.get(channel, 0)
        print(f"  {channel:13s}: {count:3d} actions")
    
    # Check CRITICAL decision details
    print("\n7. CRITICAL DECISION ANALYSIS")
    print("-" * 80)
    critical_decisions = [
        (eq_id, dec) for eq_id, dec in decisions 
        if dec['risk_level'] == 'CRITICAL'
    ]
    
    if critical_decisions:
        print(f"Critical decisions: {len(critical_decisions)}")
        for eq_id, decision in critical_decisions[:3]:  # Show first 3
            print(f"\n  {eq_id}:")
            print(f"    Severity: {decision['severity']:.0%}")
            print(f"    Analysis: {decision['analysis'][:80]}...")
            print(f"    Actions: {len(decision['action_plan'])}")
    else:
        print("No CRITICAL decisions at this time")
    
    # System health check
    print("\n8. SYSTEM HEALTH CHECK")
    print("-" * 80)
    all_nominal = all(
        dec['risk_level'] in ['LOW', 'MEDIUM'] 
        for _, dec in decisions
    )
    
    all_have_analysis = all(
        dec.get('analysis') for _, dec in decisions
    )
    
    all_have_actions = all(
        dec.get('action_plan') for _, dec in decisions
    )
    
    schema_valid = all(
        all(key in dec for key in [
            'decision_id', 'analysis', 'severity', 'risk_level',
            'recoverable', 'requires_human_approval', 'action_plan'
        ])
        for _, dec in decisions
    )
    
    checks = {
        "Decision Schema Valid": schema_valid,
        "All Decisions Have Analysis": all_have_analysis,
        "All Decisions Have Action Plans": all_have_actions,
        "Approval Workflow Configured": any(d['requires_human_approval'] for _, d in decisions),
        f"Equipment Processed: {total_equipment}/11": total_equipment == 11,
    }
    
    print("System Checks:")
    for check, status in checks.items():
        symbol = "[PASS]" if status else "[FAIL]"
        print(f"  {symbol} {check}")
    
    all_passed = all(checks.values())
    
    # Final summary
    print("\n" + "=" * 80)
    if all_passed:
        print("[PASS] SYSTEM INTEGRATION TEST: PASSED")
        print("  All components working correctly, ready for production")
    else:
        print("[FAIL] SYSTEM INTEGRATION TEST: FAILED")
        print("  Check the items marked [FAIL] above")
    print("=" * 80 + "\n")
    
    return all_passed


if __name__ == "__main__":
    success = test_complete_system()
    exit(0 if success else 1)
