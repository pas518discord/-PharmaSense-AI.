#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PharmaSense AI — Deep Decision Trees (Offline Fallback)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import time
from typing import Dict, Any, List, Optional

# ==============================================================================
# Helper Utility Functions
# ==============================================================================

def _generate_decision_id(equipment_id: str, classification: str) -> str:
    """Generates a deterministic decision tracking identifier conforming to corporate schema."""
    return f"DEC-2026-{equipment_id}-{classification.upper()}"


def _get_base_response(equipment_id: str, classification: str) -> Dict[str, Any]:
    """Pre-configures a standard baseline response contract."""
    return {
        "decision_id": _generate_decision_id(equipment_id, classification),
        "analysis": "All operational parameters satisfy authorized GxP/WHO baseline tolerances.",
        "severity": 0.10,
        "risk_level": "LOW",
        "recoverable": True,
        "requires_human_approval": False,
        "approval_message": None,
        "action_plan": []
    }


# ==============================================================================
# 1. PharmaFreezer Decision Triage Logic
# ==============================================================================

def decide_freezer(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates cold-chain data points using regulatory-compliant decision trees.
    Applies WHO and GxP standards for temperature sensitive medical assets.
    """
    eq_id = data.get("equipment_id", "UNKNOWN-FZ")
    response = _get_base_response(eq_id, "FREEZER")
    
    # Extract telemetry metrics
    temp_c = data.get("temp_c", -25.0)
    actual_temp = data.get("actual_temp_c", temp_c)
    humidity_pct = data.get("humidity_pct", 15.0)
    power_ok = data.get("power_ok", True)
    door_seal_ok = data.get("door_seal_ok", True)
    status_label = data.get("status", "NOMINAL")
    
    # Contextual metadata parameters
    product_type = data.get("product_type", "vaccine_storage")
    site_id = data.get("site_id", "site_unknown")
    
    # Calculate physics trends/discrepancies
    temp_discrepancy = abs(actual_temp - temp_c)
    
    # --- BRANCH 1: POWER FAILURE (CRITICAL) ---
    if not power_ok or status_label == "POWER_LOSS" or data.get("profile") == "power_failure":
        response.update({
            "analysis": f"CRITICAL FAULT: Total electrical power loss confirmed at asset {eq_id}. "
                        f"Temperatures are escalating actively towards critical thresholds. Risk of total asset loss.",
            "severity": 0.98,
            "risk_level": "CRITICAL",
            "recoverable": True,
            "requires_human_approval": True,
            "approval_message": "Authorize emergency deployment of mobile diesel-driven generator backups and auxiliary cooling loops.",
            "action_plan": [
                {
                    "channel": "SAFETY",
                    "action": "ACTIVATE_LOCAL_BACKUP_POWER",
                    "params": {"equipment_id": eq_id, "site_id": site_id}
                },
                {
                    "channel": "NOTIFICATION",
                    "action": "PAGE_ON_CALL_ENGINEERING",
                    "params": {"priority": "P1", "message": f"Power loss exception on {eq_id}"}
                },
                {
                    "channel": "COMPLIANCE",
                    "action": "LOG_ENVIRONMENTAL_DEVIATION",
                    "params": {"initial_temp": temp_c, "regulatory_profile": "GxP_ColdChain"}
                }
            ]
        })
        return response

    # --- BRANCH 2: TEMPERATURE EXCURSION (> 8°C AND RISING) (CRITICAL) ---
    # Since failure profiles cause continuous positive thermal step updates, a temp above 8°C implies an ongoing rising trend.
    if temp_c > 8.0:
        response.update({
            "analysis": f"CRITICAL EXCURSION: Internal compartment temperature ({temp_c}°C) exceeds maximum safe boundaries "
                        f"for {product_type}. Immediate degradation risk detected.",
            "severity": 0.95,
            "risk_level": "CRITICAL",
            "recoverable": False,
            "requires_human_approval": True,
            "approval_message": f"Emergency validation required to clear immediate cross-site payload transfer due to asset failure.",
            "action_plan": [
                {
                    "channel": "SAFETY",
                    "action": "RELOCATE_COMPROMISED_PAYLOAD_IMMEDIATELY",
                    "params": {"source_id": eq_id, "destination_site": "SECONDARY_RESERVE_VAULT", "product_type": product_type}
                },
                {
                    "channel": "COMPLIANCE",
                    "action": "HALT_ASSET_DISPENSATION_PROTOCOLS",
                    "params": {"equipment_id": eq_id, "reason": "WHO Thermal Boundary Excursion"}
                },
                {
                    "channel": "NOTIFICATION",
                    "action": "BROADCAST_FACILITY_WIDE_ALERT",
                    "params": {"severity": "CRITICAL", "scope": "PHARMA_COLD_CHAIN"}
                }
            ]
        })
        return response

    # --- BRANCH 3: SENSOR DRIFT ANOMALY (HIGH) ---
    if temp_discrepancy > 3.0 or not data.get("temp_sensor_ok", True) or data.get("profile") == "sensor_drift":
        response.update({
            "analysis": f"HIGH ANOMALY DETECTED: Significant variance ({temp_discrepancy}°C) validated between core loop "
                        f"control logic readings and secondary verification thermistors. Displayed metrics are fundamentally corrupted.",
            "severity": 0.85,
            "risk_level": "HIGH",
            "recoverable": True,
            "requires_human_approval": False, # Explicit instructions dictate requirement fields: only true for specific list
            "action_plan": [
                {
                    "channel": "MAINTENANCE",
                    "action": "FLAG_TELEMETRY_STREAM_UNRELIABLE",
                    "params": {"equipment_id": eq_id, "target_sensor": "PRIMARY_THERMISTOR_A"}
                },
                {
                    "channel": "MAINTENANCE",
                    "action": "DEPLOY_CALIBRATION_TECHNICIAN",
                    "params": {"priority": "HIGH", "equipment_id": eq_id}
                },
                {
                    "channel": "COMPLIANCE",
                    "action": "AUDIT_HISTORICAL_LOGGING_WINDOW",
                    "params": {"lookback_hours": 24, "equipment_id": eq_id}
                }
            ]
        })
        return response

    # --- BRANCH 4: SUSTAINED HIGH TEMPERATURE WARNING (HIGH) ---
    # Cover warning thresholds transitioning over standard baseline tolerances
    if temp_c > 5.0 or status_label == "TEMP_WARNING":
        response.update({
            "analysis": f"HIGH WARNING: Compartment telemetry has drifted past 5.0°C. Long-term compliance "
                        f"tolerances are eroding. Compressor asset checks and active observation required.",
            "severity": 0.75,
            "risk_level": "HIGH",
            "recoverable": True,
            "requires_human_approval": False,
            "action_plan": [
                {
                    "channel": "MAINTENANCE",
                    "action": "TRIGGER_COMPRESSOR_DIAGNOSTIC_SUITE",
                    "params": {"equipment_id": eq_id}
                },
                {
                    "channel": "NOTIFICATION",
                    "action": "ALERT_DUTY_PHARMACIST",
                    "params": {"message": f"Asset {eq_id} thermal metrics approaching degradation levels.", "current_temp": temp_c}
                }
            ]
        })
        return response

    # --- BRANCH 5: DOOR SEAL BREACH WITH HUMIDITY ACCUMULATION (MEDIUM) ---
    if not door_seal_ok or humidity_pct > 60.0 or data.get("profile") == "door_seal_breach":
        response.update({
            "analysis": f"MEDIUM DEVIATION: External atmospheric air ingress confirmed. Gasket failure or open door state "
                        f"causing excessive internal moisture build-up ({humidity_pct}%).",
            "severity": 0.45,
            "risk_level": "MEDIUM",
            "recoverable": True,
            "requires_human_approval": False,
            "action_plan": [
                {
                    "channel": "MAINTENANCE",
                    "action": "SCHEDULE_CHASSIS_SEAL_REPLACEMENT",
                    "params": {"equipment_id": eq_id, "window_allowed_hours": 12}
                },
                {
                    "channel": "COMPLIANCE",
                    "action": "INSPECT_FOR_COMPARTMENT_FROST_ACCUMULATION",
                    "params": {"equipment_id": eq_id}
                }
            ]
        })
        return response

    return response


# ==============================================================================
# 2. DrugDispenser Decision Triage Logic
# ==============================================================================

def decide_dispenser(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates automated point-of-use distribution cabinet telemetry metrics
    against site security protocols and storage limits.
    """
    eq_id = data.get("equipment_id", "UNKNOWN-DD")
    response = _get_base_response(eq_id, "DISPENSER")
    
    unusual_access = data.get("unusual_access", False)
    access_count_24h = data.get("access_count_24h", 0)
    motor_ok = data.get("motor_ok", True)
    inventory_pct = data.get("inventory_pct", 100.0)
    temp_c = data.get("temp_c", 20.0)
    product_type = data.get("product_type", "general_meds")
    
    # --- BRANCH 1: SECURITY ACCESS ANOMALY (HIGH / APPROVAL REQUIRED) ---
    if unusual_access or access_count_24h > 50 or data.get("profile") == "access_anomaly":
        response.update({
            "analysis": f"HIGH SECURITY EXCEPTION: Chain-of-custody profile anomaly detected on {eq_id}. "
                        f"Unusual scheduling or repeated rapid extraction vectors challenge facility authorization profiles.",
            "severity": 0.88,
            "risk_level": "HIGH",
            "recoverable": True,
            "requires_human_approval": True,  # Explicitly required per prompt for access_anomaly
            "approval_message": "Immediate operational sign-off needed to remote-unlock automated locking assemblies.",
            "action_plan": [
                {
                    "channel": "SAFETY",
                    "action": "LOCK_DISPENSATION_VAULT_CHASSIS",
                    "params": {"equipment_id": eq_id}
                },
                {
                    "channel": "NOTIFICATION",
                    "action": "PAGE_FACILITY_PHYSICAL_SECURITY",
                    "params": {"alert_code": "SEC_ALPHA_01", "location_target": eq_id, "active_user": data.get("last_access_user")}
                },
                {
                    "channel": "COMPLIANCE",
                    "action": "EXPORT_CHAIN_OF_CUSTODY_AUDIT_LOG",
                    "params": {"lookback_hours": 24, "target_device": eq_id}
                }
            ]
        })
        return response

    # --- BRANCH 2: TEMPERATURE OUT OF CONTROLLED ROOM RANGE (HIGH) ---
    if temp_c < 15.0 or temp_c > 25.0 or data.get("profile") == "temp_out_of_range":
        response.update({
            "analysis": f"HIGH ENVIRONMENTAL ALERT: Cabinet internal atmosphere ({temp_c}°C) has escaped authorized "
                        f"Controlled Room Temperature bounds (15.0°C - 25.0°C). Product efficacy requires evaluation.",
            "severity": 0.82,
            "risk_level": "HIGH",
            "recoverable": True,
            "requires_human_approval": False,
            "action_plan": [
                {
                    "channel": "COMPLIANCE",
                    "action": "FLAG_DISPENSED_BATCHES_SINCE_EXCURSION",
                    "params": {"equipment_id": eq_id, "excursion_timestamp": data.get("timestamp")}
                },
                {
                    "channel": "MAINTENANCE",
                    "action": "ENGAGE_AUXILIARY_HVAC_BALANCING",
                    "params": {"location_id": data.get("site_id")}
                }
            ]
        })
        return response

    # --- BRANCH 3: MOTOR DRIVETRAIN JAM (HIGH) ---
    if not motor_ok or data.get("profile") == "motor_jam" or data.get("dispense_accuracy_pct", 100.0) < 90.0:
        response.update({
            "analysis": f"HIGH MECHANICAL FAILURE: Actuator drivetrain lockup or drawer mechanical stall verified on {eq_id}. "
                        f"Physical deployment mechanisms are incapacitated.",
            "severity": 0.78,
            "risk_level": "HIGH",
            "recoverable": True,
            "requires_human_approval": False,
            "action_plan": [
                {
                    "channel": "SAFETY",
                    "action": "DISABLE_DISPENSER_LOCKOUT_LOOPS",
                    "params": {"equipment_id": eq_id}
                },
                {
                    "channel": "NOTIFICATION",
                    "action": "ROUTE_REQUESTS_TO_MANUAL_STATION",
                    "params": {"backup_station_id": "MANUAL_DESK_PRIMARY", "product_category": product_type}
                },
                {
                    "channel": "MAINTENANCE",
                    "action": "DISPATCH_MECHANICAL_REPAIR_TEAM",
                    "params": {"equipment_id": eq_id, "reason": "Actuator Jam"}
                }
            ]
        })
        return response

    # --- BRANCH 4: INVENTORY DEPLETION WARNING (MEDIUM) ---
    if inventory_pct < 10.0 or data.get("profile") == "inventory_low":
        response.update({
            "analysis": f"MEDIUM SUPPLY ALERT: Total available inventory levels inside storage modules have fallen to "
                        f"{inventory_pct}%. Immediate logistics replenishment required to avoid an out-of-stock emergency.",
            "severity": 0.40,
            "risk_level": "MEDIUM",
            "recoverable": True,
            "requires_human_approval": False,
            "action_plan": [
                {
                    "channel": "COMPLIANCE",
                    "action": "TRIGGER_AUTOMATED_REORDER_PIPELINE",
                    "params": {"item_profile": product_type, "target_replenish_pct": 100.0, "requesting_unit": eq_id}
                }
            ]
        })
        return response

    return response


# ==============================================================================
# 3. BloodStorage Decision Triage Logic
# ==============================================================================

def decide_blood_storage(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates mission-critical blood storage infrastructure telemetry variables 
    enforcing severe AABB/FDA metabolic and regulatory guardrails.
    """
    eq_id = data.get("equipment_id", "UNKNOWN-BS")
    response = _get_base_response(eq_id, "BLOOD_STORAGE")
    
    temp_c = data.get("temp_c", 4.0)
    units_expiring_48h = data.get("units_expiring_48h", 0)
    co2_ppm = data.get("co2_ppm", 380.0)
    contamination_risk_pct = data.get("contamination_risk_pct", 0.0)
    
    # --- BRANCH 1: FREEZING TEMPERATURE VIOLATION (CRITICAL) ---
    if temp_c < 1.0:
        response.update({
            "analysis": f"CRITICAL THERMAL EXCURSION: Compartment temperature ({temp_c}°C) fell below minimum biological limits (1.0°C). "
                        f"Irreversible red blood cell lysis and physical cellular shattering risks are imminent.",
            "severity": 0.99,
            "risk_level": "CRITICAL",
            "recoverable": False,
            "requires_human_approval": True,
            "approval_message": "Immediate management clearance needed to run structural destruction protocols on frozen blood units.",
            "action_plan": [
                {
                    "channel": "SAFETY",
                    "action": "QUARANTINE_CONGEALED_BIOLOGICAL_ASSETS",
                    "params": {"equipment_id": eq_id, "temperature_observed": temp_c}
                },
                {
                    "channel": "COMPLIANCE",
                    "action": "SUSPEND_BLOOD_BANK_BANKING_OPERATIONS",
                    "params": {"equipment_id": eq_id}
                },
                {
                    "channel": "NOTIFICATION",
                    "action": "ESCALATE_TO_CHIEF_MEDICAL_OFFICER",
                    "params": {"incident_class": "THERMAL_FREEZE_SPOILAGE", "asset": eq_id}
                }
            ]
        })
        return response

    # --- BRANCH 2: OVERHEATING TEMPERATURE VIOLATION (CRITICAL) ---
    if temp_c > 6.0 or data.get("profile") == "temp_excursion":
        response.update({
            "analysis": f"CRITICAL THERMAL EXCURSION: Internal storage environment ({temp_c}°C) exceeds maximum regulated biological "
                        f"limits (6.0°C). Proliferative bacterial growth vectors present. High likelihood of product discard.",
            "severity": 0.96,
            "risk_level": "CRITICAL",
            "recoverable": False,
            "requires_human_approval": True,
            "approval_message": "Acknowledge biological risk and authorize immediate systemic quarantine of matching product series numbers.",
            "action_plan": [
                {
                    "channel": "SAFETY",
                    "action": "QUARANTINE_OVERHEATED_BIOLOGICAL_ASSETS",
                    "params": {"equipment_id": eq_id, "temperature_observed": temp_c}
                },
                {
                    "channel": "COMPLIANCE",
                    "action": "ENFORCE_DISCARD_EVALUATION_HOLD",
                    "params": {"equipment_id": eq_id, "regulatory_body": "AABB_FDA_THRESHOLD"}
                }
            ]
        })
        return response

    # --- BRANCH 3: BIOLOGICAL METABOLIC CO2 CONTAMINATION ANOMALY (HIGH) ---
    if co2_ppm > 1000.0 or contamination_risk_pct > 10.0 or data.get("profile") == "contamination_risk":
        response.update({
            "analysis": f"HIGH ANOMALY DETECTED: Carbon dioxide concentrations ({co2_ppm} ppm) suggest catastrophic microbial proliferation, "
                        f"organic decomposition trends, or severe structural sealing decay within containment boundaries.",
            "severity": 0.86,
            "risk_level": "HIGH",
            "recoverable": True,
            "requires_human_approval": True,  # Explicitly required per prompt for blood_contamination_risk
            "approval_message": "Approve urgent internal decontamination cycle and secondary gas sensor diagnostic sweep.",
            "action_plan": [
                {
                    "channel": "SAFETY",
                    "action": "ISOLATE_ATMOSPHERIC_ENVIRONMENT",
                    "params": {"equipment_id": eq_id}
                },
                {
                    "channel": "MAINTENANCE",
                    "action": "PERFORM_SEAL_INTEGRITY_INVESTIGATION",
                    "params": {"equipment_id": eq_id}
                },
                {
                    "channel": "COMPLIANCE",
                    "action": "EXECUTE_BIOLOGICAL_ASSAY_SAMPLING",
                    "params": {"equipment_id": eq_id, "sample_volume_ml": 5.0}
                }
            ]
        })
        return response

    # --- BRANCH 4: SHELF-LIFE EXPIRATION MATRIX ALERT (MEDIUM) ---
    if units_expiring_48h > 5 or data.get("profile") == "unit_expiry":
        response.update({
            "analysis": f"MEDIUM LIFE-CYCLE ALERT: Total of {units_expiring_48h} whole blood units are crossing regulatory "
                        f"42-day preservation storage limits within 48 hours. Inventory utilization optimization required.",
            "severity": 0.50,
            "risk_level": "MEDIUM",
            "recoverable": True,
            "requires_human_approval": False,
            "action_plan": [
                {
                    "channel": "NOTIFICATION",
                    "action": "ALERT_BLOOD_BANK_COORDINATOR",
                    "params": {"affected_units_count": units_expiring_48h, "timeframe_remaining": "48h"}
                },
                {
                    "channel": "COMPLIANCE",
                    "action": "REPRIORITIZE_FIRST_EXPIRY_FIRST_OUT_QUEUE",
                    "params": {"equipment_id": eq_id}
                }
            ]
        })
        return response

    return response


# ==============================================================================
# 4. Fleet-Level Multi-Facility Coordination Decision Engine
# ==============================================================================

def decide_fleet(site_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates enterprise-wide multi-facility operational trends to capture cascading 
    regional infrastructure failures and orchestrate large-scale emergency logistics.
    """
    response = {
        "decision_id": "DEC-2026-GLOBAL-FLEET-COORDINATION",
        "analysis": "All cross-site monitoring telemetry displays nominal operational balance.",
        "severity": 0.10,
        "risk_level": "LOW",
        "recoverable": True,
        "requires_human_approval": False,
        "approval_message": None,
        "action_plan": []
    }
    
    # Process site aggregations
    sites_failing = site_metrics.get("sites_failing_count", 0)
    total_power_loss_detected = site_metrics.get("site_wide_power_loss", False)
    emergency_transfer_requested = site_metrics.get("emergency_transfer_required", False)
    
    # --- BRANCH 1: CASCADING MULTI-SITE CRITICAL INFRASTRUCTURE SHUTDOWN ---
    if total_power_loss_detected or sites_failing >= 2:
        response.update({
            "analysis": "CRITICAL FLEET ANOMALY: Cascading multi-site infrastructure power failure or multi-facility environmental "
                        "bounds collapse validated. Enterprise asset integrity compromised. Activating disaster recovery runbooks.",
            "severity": 0.97,
            "risk_level": "CRITICAL",
            "recoverable": True,
            "requires_human_approval": True,
            "approval_message": "Authorize massive regional product transit diversion protocols and external cold storage supply locks.",
            "action_plan": [
                {
                    "channel": "SAFETY",
                    "action": "EXECUTE_REGIONAL_CASCADE_CONTAINMENT_RUNBOOK",
                    "params": {"affected_sites_count": sites_failing}
                },
                {
                    "channel": "MAINTENANCE",
                    "action": "DIVERT_POWER_GRID_RESERVES",
                    "params": {"priority_facilities": site_metrics.get("critical_facilities_list", ["site_a", "site_b"])}
                },
                {
                    "channel": "NOTIFICATION",
                    "action": "ESCALATE_TO_ENTERPRISE_DISASTER_LOGISTICS",
                    "params": {"incident_level": "TIER_1_REGIONAL"}
                }
            ]
        })
        return response

    # --- BRANCH 2: COMPARTMENT TRANSFER LOGISTICS EXCEPTION ---
    if emergency_transfer_requested:
        response.update({
            "analysis": "HIGH LOGISTICS INTERVENTION: Isolated asset degradation patterns dictate immediate "
                        "inter-facility logistics re-routing to guarantee baseline cold-chain compliance metrics.",
            "severity": 0.70,
            "risk_level": "HIGH",
            "recoverable": True,
            "requires_human_approval": False,
            "action_plan": [
                {
                    "channel": "SAFETY",
                    "action": "ORCHESTRATE_INTER_SITE_PRODUCT_TRANSFER",
                    "params": {
                        "origin_facility": site_metrics.get("source_site", "site_a"),
                        "receiving_facility": site_metrics.get("destination_site", "site_b"),
                        "transit_configuration": "ACTIVE_DRY_ICE_LOOPS"
                    }
                }
            ]
        })
        return response

    return response


# ==============================================================================
# 5. Core Operational Triage Dispatcher
# ==============================================================================

def triage(appliance_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Central dispatcher evaluating inbound data tracking formats, identifying asset 
    classifications, and routing metrics to matching decision engine layers.
    """
    equipment_type = appliance_data.get("equipment_type", "")
    
    if equipment_type == "PharmaFreezer":
        return decide_freezer(appliance_data)
    elif equipment_type == "DrugDispenser":
        return decide_dispenser(appliance_data)
    elif equipment_type == "BloodStorage":
        return decide_blood_storage(appliance_data)
    
    # Fallback default response for unclassified assets
    eq_id = appliance_data.get("equipment_id", "UNKNOWN-ASSET")
    return {
        "decision_id": _generate_decision_id(eq_id, "UNCLASSIFIED"),
        "analysis": f"ERROR: Asset classification token '{equipment_type}' does not map to active triage processing blocks.",
        "severity": 0.50,
        "risk_level": "MEDIUM",
        "recoverable": False,
        "requires_human_approval": False,
        "approval_message": None,
        "action_plan": []
    }


# ==============================================================================
# Execution Validation Context Verification Block
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("PharmaSense AI — Core Decision Tree Offline Triage Suite Verification")
    print("=" * 80)
    
    # Mock telemetry sample matrix inputs
    test_freezer_critical = {
        "equipment_id": "FZ-01",
        "equipment_type": "PharmaFreezer",
        "profile": "compressor_failure",
        "site_id": "site_a",
        "product_type": "vaccine_storage",
        "temp_c": 9.4,
        "actual_temp_c": 9.4,
        "humidity_pct": 18.0,
        "power_ok": True,
        "status": "TEMP_CRITICAL"
    }
    
    test_dispenser_security = {
        "equipment_id": "DD-01",
        "equipment_type": "DrugDispenser",
        "profile": "access_anomaly",
        "site_id": "site_a",
        "product_type": "controlled_substances",
        "temp_c": 19.8,
        "unusual_access": True,
        "access_count_24h": 72,
        "last_access_user": "UNKNOWN_UID_99"
    }
    
    print("\nExecuting live operational evaluation testing on standalone assets:\n")
    
    for mock_telemetry in [test_freezer_critical, test_dispenser_security]:
        evaluated_decision = triage(mock_telemetry)
        print(f"Asset evaluated : {mock_telemetry['equipment_id']} ({mock_telemetry['equipment_type']})")
        print(f"Decision ID     : {evaluated_decision['decision_id']}")
        print(f"Risk Assessment : {evaluated_decision['risk_level']} (Severity Weight: {evaluated_decision['severity']})")
        print(f"Approval Target : Requires Sign-Off = {evaluated_decision['requires_human_approval']}")
        if evaluated_decision['approval_message']:
            print(f"Approval Msg    : {evaluated_decision['approval_message']}")
        print("Generated Actions:")
        for action in evaluated_decision['action_plan']:
            print(f"  - [{action['channel']}] -> {action['action']} | Config Matrix: {action['params']}")
        print("-" * 80)