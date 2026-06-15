#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PharmaSense AI - Advanced Integration Examples

Demonstrates integration patterns with monitoring systems, time-series databases,
and alerting platforms.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import json
from datetime import datetime, timedelta
from pharma_sense_ai import mock_db, predict_failure


def example_1_continuous_monitoring():
    """Example: Continuous monitoring with regular snapshots."""
    print("=" * 80)
    print("EXAMPLE 1: Continuous Monitoring - 24 Hour Simulation")
    print("=" * 80)
    
    db = mock_db()
    
    # Simulate 24 hours in 2-hour increments
    hours_to_simulate = 24
    dt_hours = 2
    num_steps = hours_to_simulate // dt_hours
    
    critical_events = []
    
    for step in range(num_steps):
        current_time = datetime.now() + timedelta(hours=step * dt_hours)
        
        # Step all equipment
        for category, equipment_list in db.items():
            for equipment in equipment_list:
                equipment.step(dt_hours)
                
                # Get snapshot
                snapshot = equipment.snapshot(current_time)
                
                # Get prediction
                prediction = predict_failure(snapshot)
                
                # Track critical predictions
                if prediction["confidence"] > 0.85:
                    critical_events.append({
                        "time": current_time.isoformat(),
                        "equipment_id": equipment.equipment_id,
                        "status": snapshot["status"],
                        "predicted_failure": prediction["predicted_failure"],
                        "confidence": prediction["confidence"],
                        "time_to_critical": prediction["time_to_critical_hours"],
                    })
    
    print(f"\nSimulated {hours_to_simulate} hours ({num_steps} steps)")
    print(f"\nCritical Events Detected ({len(critical_events)}):")
    print("-" * 80)
    
    for event in critical_events:
        print(f"\n{event['time']} | {event['equipment_id']}")
        print(f"  Status: {event['status']}")
        print(f"  Predicted Failure: {event['predicted_failure']}")
        print(f"  Confidence: {event['confidence']:.0%}")
        print(f"  Time to Critical: {event['time_to_critical']:.1f} hours")


def example_2_json_export():
    """Example: Export snapshots as JSON for downstream systems."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: JSON Export for Data Pipeline")
    print("=" * 80)
    
    db = mock_db()
    
    # Simulate equipment and export JSON
    equipment = db["pharma_freezers"][0]  # FZ-01 with compressor failure
    
    print(f"\nExporting {equipment.equipment_id} state changes:")
    print("-" * 80)
    
    snapshots = []
    for hour in range(5):
        equipment.step(1.0)
        snapshot = equipment.snapshot(datetime.now() + timedelta(hours=hour))
        snapshots.append(snapshot)
    
    # Export as JSON lines (compatible with streaming pipelines)
    for i, snapshot in enumerate(snapshots):
        json_line = json.dumps(snapshot)
        print(f"\nSnapshot {i+1}:")
        print(json_line)
    
    # Example Splunk HEC format
    print("\n\nExample Splunk HEC Format:")
    print("-" * 80)
    for snapshot in snapshots[:2]:  # Just show first 2
        hec_event = {
            "time": datetime.fromisoformat(snapshot["timestamp"]).timestamp(),
            "source": f"pharma_sense/equipment/{snapshot['equipment_id']}",
            "sourcetype": "pharma_simulation",
            "event": snapshot
        }
        print(json.dumps(hec_event, indent=2))


def example_3_predictive_analytics():
    """Example: Predictive analytics - detect failures early."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Early Failure Detection")
    print("=" * 80)
    
    db = mock_db()
    
    # Focus on sensor drift unit (subtle failure)
    sensor_drift_unit = db["pharma_freezers"][4]  # FZ-05
    
    print(f"\nMonitoring {sensor_drift_unit.equipment_id} ({sensor_drift_unit.profile})")
    print("Sensor drift is a subtle failure - displayed temp looks normal but actual temp rises")
    print("-" * 80)
    
    for hour in range(1, 16):
        sensor_drift_unit.step(1.0)
        snapshot = sensor_drift_unit.snapshot(datetime.now())
        prediction = predict_failure(snapshot)
        
        if hour % 3 == 0:  # Print every 3 hours
            print(f"\nHour {hour}:")
            print(f"  Displayed Temperature: {snapshot['temp_c']:.2f}C (appears normal)")
            print(f"  Actual Temperature:    {snapshot['actual_temp_c']:.2f}C (hidden)")
            print(f"  Status: {snapshot['status']}")
            print(f"  Predicted: {prediction['predicted_failure']} ({prediction['confidence']:.0%})")
            print(f"  Time to Critical: {prediction['time_to_critical_hours']:.1f} hours")


def example_4_multi_site_analytics():
    """Example: Analyze equipment across multiple sites."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Multi-Site Analytics")
    print("=" * 80)
    
    db = mock_db()
    
    # Simulate 5 hours
    for _ in range(10):
        for category, equipment_list in db.items():
            for equipment in equipment_list:
                equipment.step(0.5)
    
    # Analyze by site
    sites = {}
    for category, equipment_list in db.items():
        for equipment in equipment_list:
            site = equipment.site_name
            if site not in sites:
                sites[site] = {
                    "equipment": [],
                    "critical_alerts": 0,
                    "warnings": 0,
                }
            
            snapshot = equipment.snapshot(datetime.now())
            prediction = predict_failure(snapshot)
            
            sites[site]["equipment"].append({
                "id": equipment.equipment_id,
                "type": snapshot["equipment_type"],
                "status": snapshot["status"],
                "prediction": prediction["predicted_failure"],
                "confidence": prediction["confidence"],
            })
            
            if prediction["confidence"] > 0.85:
                sites[site]["critical_alerts"] += 1
            elif prediction["confidence"] > 0.60:
                sites[site]["warnings"] += 1
    
    print("\nSite Health Summary:")
    print("-" * 80)
    print(f"{'Site':<10} {'Equipment':<10} {'Critical':<10} {'Warnings':<10} {'Status':<30}")
    print("-" * 80)
    
    for site_name in sorted(sites.keys()):
        site_data = sites[site_name]
        equipment_count = len(site_data["equipment"])
        critical = site_data["critical_alerts"]
        warnings = site_data["warnings"]
        
        # Determine health status
        if critical > 0:
            status = f"CRITICAL ({critical} alerts)"
        elif warnings > 0:
            status = f"WARNING ({warnings} alerts)"
        else:
            status = "NOMINAL"
        
        print(f"{site_name:<10} {equipment_count:<10} {critical:<10} {warnings:<10} {status:<30}")
        
        # List each equipment
        for eq in site_data["equipment"]:
            if eq["confidence"] > 0.60:
                print(f"{'':10}   - {eq['id']:<8} {eq['type']:<20} {eq['prediction']:<20}")


def example_5_alert_rules():
    """Example: Define and execute alert rules."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Alert Rules Engine")
    print("=" * 80)
    
    db = mock_db()
    
    # Define alert rules
    alert_rules = [
        {
            "name": "Critical Temperature Excursion",
            "condition": lambda s, p: p["confidence"] > 0.90 and "TEMP" in p["predicted_failure"],
            "severity": "CRITICAL",
            "action": "escalate_to_oncall"
        },
        {
            "name": "Sensor Malfunction Suspected",
            "condition": lambda s, p: p["predicted_failure"] == "SENSOR_DRIFT",
            "severity": "HIGH",
            "action": "notify_engineering"
        },
        {
            "name": "Access Anomaly Detected",
            "condition": lambda s, p: p["predicted_failure"] == "ACCESS_ANOMALY_DETECTED",
            "severity": "HIGH",
            "action": "notify_security"
        },
        {
            "name": "Maintenance Warning",
            "condition": lambda s, p: 0.60 < p["confidence"] < 0.85,
            "severity": "MEDIUM",
            "action": "schedule_maintenance"
        },
    ]
    
    # Simulate and check rules
    for _ in range(10):
        for category, equipment_list in db.items():
            for equipment in equipment_list:
                equipment.step(0.5)
    
    # Evaluate all equipment against rules
    alerts_fired = []
    for category, equipment_list in db.items():
        for equipment in equipment_list:
            snapshot = equipment.snapshot(datetime.now())
            prediction = predict_failure(snapshot)
            
            for rule in alert_rules:
                if rule["condition"](snapshot, prediction):
                    alerts_fired.append({
                        "equipment_id": equipment.equipment_id,
                        "rule": rule["name"],
                        "severity": rule["severity"],
                        "action": rule["action"],
                        "failure": prediction["predicted_failure"],
                        "confidence": prediction["confidence"],
                    })
    
    print(f"\nAlerts Fired: {len(alerts_fired)}")
    print("-" * 80)
    
    for alert in alerts_fired:
        print(f"\n[{alert['severity']}] {alert['rule']}")
        print(f"  Equipment: {alert['equipment_id']}")
        print(f"  Failure Type: {alert['failure']}")
        print(f"  Confidence: {alert['confidence']:.0%}")
        print(f"  Action: {alert['action']}")


def main():
    """Run all examples."""
    example_1_continuous_monitoring()
    example_2_json_export()
    example_3_predictive_analytics()
    example_4_multi_site_analytics()
    example_5_alert_rules()
    
    print("\n" + "=" * 80)
    print("ALL EXAMPLES COMPLETED")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
