#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PharmaSense AI — Unit Test Suite

Comprehensive pytest test suite validating physics simulation trends, 
sensor discrepancies, security states, predictive models, missing value safeguards, 
and decision orchestration schema validation.

Usage:
    pytest -v test_pharma_sense.py
"""

import math
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pharma_sense_ai import (
    PharmaFreezer,
    DrugDispenser,
    BloodStorage,
    mock_db,
    predict_failure,
    triage,
    EquipmentStatus
)


def test_pharma_freezer_compressor_failure():
    """
    Validates that a PharmaFreezer experiencing a compressor failure 
    exhibits a monotonic warming trend, drifts beyond threshold tolerances, 
    and raises appropriate high-severity operational state flags.
    """
    freezer = PharmaFreezer("TEST-FZ-FAIL", profile="compressor_failure")
    initial_snapshot = freezer.snapshot(datetime.now())
    initial_temp = initial_snapshot["temp_c"]
    
    previous_temp = initial_temp
    dt_hours = 1.0
    
    # Run 8 steps of 1 hour each
    for _ in range(8):
        freezer.step(dt_hours)
        current_snapshot = freezer.snapshot(datetime.now())
        current_temp = current_snapshot["temp_c"]
        
        # Assert temperature increases each step (warming trend)
        assert current_temp > previous_temp, f"Temperature did not increase: {current_temp} <= {previous_temp}"
        previous_temp = current_temp

    final_snapshot = freezer.snapshot(datetime.now())
    final_temp = final_snapshot["temp_c"]
    
    # Assert final temp_c shifted at least 3.0 degrees from baseline
    assert final_temp > initial_temp + 3.0, f"Insufficient thermal degradation: {final_temp} <= {initial_temp + 3.0}"
    
    # Assert status is escalated appropriately
    status = final_snapshot["status"]
    assert status in (EquipmentStatus.TEMP_WARNING.value, EquipmentStatus.TEMP_CRITICAL.value, EquipmentStatus.COMPRESSOR_FAIL.value), \
        f"Unexpected system status code logged: {status}"


def test_pharma_freezer_sensor_drift():
    """
    Validates compliance against hidden environmental vulnerabilities where the displayed 
    telemetry diverges significantly from true atmospheric physics while marking flags.
    """
    freezer = PharmaFreezer("TEST-FZ-DRIFT", profile="sensor_drift")
    
    # Run long enough to exceed the 5C sensor drift threshold at 0.5C/hour.
    for _ in range(12):
        freezer.step(1.0)
        
    snapshot = freezer.snapshot(datetime.now())
    
    # Assert snapshot has "actual_temp_c" field mapping core physics
    assert "actual_temp_c" in snapshot, "Critical payload deficiency: actual_temp_c field missing"
    
    displayed_temp = snapshot["temp_c"]
    actual_temp = snapshot["actual_temp_c"]
    
    # Assert absolute sensor error variance exceeds threshold drift bounds (> 5 units)
    assert abs(actual_temp - displayed_temp) > 5.0, \
        f"Sensor drift tolerance divergence failed. Displayed: {displayed_temp}, Actual: {actual_temp}"
        
    # Assert hardware diagnosis indicator flags broken component status
    assert snapshot["temp_sensor_ok"] is False, "Hardware circuit component map erroneously marked clean"


def test_drug_dispenser_access_anomaly():
    """
    Verifies immediate enforcement of compliance locks and authorization alerts 
    when specialized cryptographic or security boundary anomalies occur.
    """
    dispenser = DrugDispenser("TEST-DD-ANOM", profile="access_anomaly")
    snapshot = dispenser.snapshot(datetime.now())
    
    # Assert physical sensor indicators flag suspicious interface signatures
    assert snapshot["unusual_access"] is True, "Security validation failed to latch unusual_access flag"
    
    # Assert state engine moves immediately to automated secure lockdown labels
    assert snapshot["status"] == EquipmentStatus.ACCESS_ANOMALY.value, \
        f"Security perimeter status validation mismatch: {snapshot['status']}"


def test_blood_storage_temp_excursion():
    """
    Ensures safe biological containment rulesets trigger predictive maintenance schedules 
    before critical thermal thresholds breach WHO viability boundaries.
    """
    refrigerator = BloodStorage("TEST-BS-EXC", profile="temp_excursion")
    
    # Step forward to trigger accelerated warming models
    for _ in range(3):
        refrigerator.step(1.0)
        
    snapshot = refrigerator.snapshot(datetime.now())
    
    # Assert biological target safety bounds exceeded (> 6.0C limit)
    assert snapshot["temp_c"] > 6.0, f"Biological agent thermal boundary unbroken: {snapshot['temp_c']}°C"
    
    # Evaluate forecasting models
    prediction = predict_failure(snapshot)
    
    # Assert predictive certainty algorithms register actionable confidence limits (> 0.85)
    assert prediction["confidence"] > 0.85, \
        f"Predictive anomaly classifier yielded insufficient telemetry confidence: {prediction['confidence']}"


def test_predict_failure_all_appliances():
    """
    Validates end-to-end telemetry schemas and structured predictive properties across 
    the entire fleet inventory mapping matrices.
    """
    db = mock_db()
    
    for category, equipment_list in db.items():
        for appliance in equipment_list:
            snapshot = appliance.snapshot(datetime.now())
            prediction = predict_failure(snapshot)
            
            # Assert all structural components exist in payload mapping schemas
            for key in ["predicted_failure", "confidence", "root_cause"]:
                assert key in prediction, f"Missing payload definition block key target '{key}' in {appliance.equipment_id}"
                
            # Assert classification probability sits tightly bounded inside standard real spaces [0.0, 1.0]
            conf = prediction["confidence"]
            assert isinstance(conf, (int, float)), f"Type error: confidence score payload mapping corrupted in {appliance.equipment_id}"
            assert 0.0 <= conf <= 1.0, f"Confidence boundary rupture: value {conf} out of index parameters"
            
            # Continuous data integration scan verifying zero math exceptions present inside fields
            for field, value in snapshot.items():
                if isinstance(value, float):
                    assert not math.isnan(value), f"NaN float mapping failure inside {appliance.equipment_id} -> field: {field}"
                    assert not math.isinf(value), f"Infinity bounds overflow anomaly inside {appliance.equipment_id} -> field: {field}"


def test_no_nan_values_20_runs():
    """
    Robustness testing to guarantee float parameters remain fully determined 
    and free of missing data defects under continuous randomized initializations.
    """
    for run_idx in range(20):
        db = mock_db()
        for category, equipment_list in db.items():
            for appliance in equipment_list:
                # Execute variable duty cycle steps to stress internal physics boundaries
                appliance.step(0.5)
                snapshot = appliance.snapshot(datetime.now())
                
                # Assert entire telemetry structure contains no mathematical exceptions
                for field, value in snapshot.items():
                    if isinstance(value, float):
                        assert not math.isnan(value), \
                            f"[Run {run_idx}] NaN floating point error found in asset {appliance.equipment_id} on field: {field}"
                        assert not math.isinf(value), \
                            f"[Run {run_idx}] Inf mathematical boundary exception in asset {appliance.equipment_id} on field: {field}"


def test_decision_trees_match_schema():
    """
    Validates structural compliance of edge-computed triage decision trees 
    against downstream machine interfaces and human oversight workflow gates.
    """
    db = mock_db()
    required_keys = [
        "decision_id", "analysis", "severity", "risk_level", 
        "recoverable", "requires_human_approval", "action_plan"
    ]
    valid_risk_levels = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    
    for category, equipment_list in db.items():
        for appliance in equipment_list:
            # Advance simulation timelines to ensure non-trivial diagnostics can compile
            appliance.step(2.0)
            snapshot = appliance.snapshot(datetime.now())
            decision = triage(snapshot)
            
            # Assert all required keys are structurally present inside decision payload object
            for key in required_keys:
                assert key in decision, \
                    f"Decision schema violation: missing core field parameter block '{key}' for asset {appliance.equipment_id}"
                    
            # Assert severity scores comply with standardized real space parameters [0.0, 1.0]
            severity = decision["severity"]
            assert 0.0 <= severity <= 1.0, \
                f"Validation index error: severity parameter {severity} cracked standard bounds on {appliance.equipment_id}"
                
            # Assert categorical threat classification maps exactly to corporate audit criteria
            risk = decision["risk_level"]
            assert risk in valid_risk_levels, \
                f"Payload type constraint invalid: token label '{risk}' unrecognized for asset {appliance.equipment_id}"
                
            # Human-in-the-Loop Workflow Guard: Critical items MUST trigger verification pathways
            if risk == "CRITICAL":
                assert decision["requires_human_approval"] is True, \
                    f"Compliance workflow breach: critical hazard on asset {appliance.equipment_id} bypassed human authorization gates"


if __name__ == "__main__":
    tests = [
        test_pharma_freezer_compressor_failure,
        test_pharma_freezer_sensor_drift,
        test_drug_dispenser_access_anomaly,
        test_blood_storage_temp_excursion,
        test_predict_failure_all_appliances,
        test_no_nan_values_20_runs,
        test_decision_trees_match_schema,
    ]

    for test in tests:
        test()
        print(f"[PASS] {test.__name__}")

    print("[PASS] dashboard simulation tests completed")
