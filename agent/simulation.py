#!/usr/bin/env python3
# -*- coding: utf-8 -- *
"""
PharmaSense AI — Pharmaceutical Equipment Simulation Engine

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

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, List

# ==============================================================================
# 1. PharmaFreezer Implementation
# ==============================================================================

class PharmaFreezer:
    """
    Simulates ultra-low temperature pharmaceutical freezers with realistic
    thermodynamic degradation and state tracking based on historical failure modes.
    """
    def __init__(self, equipment_id: str, profile: str = "nominal", product_type: str = "vaccine_storage", site_id: str = "site_a"):
        self.equipment_id = equipment_id
        self.profile = profile
        self.product_type = product_type
        self.site_id = site_id
        
        # Base standards & target baseline fields
        self.target_temp = -25.0  # Safe range midpoint (-20°C to -80°C standard base)
        self.ambient_temp = 22.0
        
        # Telemetry Fields
        self.temp_c = self.target_temp
        self.actual_temp_c = self.target_temp
        self.humidity_pct = 15.0
        self.compressor_ok = True
        self.door_seal_ok = True
        self.door_open_count = 0
        self.power_ok = True
        self.temp_sensor_ok = True
        self.vibration_g = 0.05
        self.coolant_pressure_bar = 12.0
        self.product_count = 1250
        
        # Apply Profile Initial States
        self._apply_profile_states()

    def _apply_profile_states(self):
        if self.profile == "compressor_failure":
            self.compressor_ok = False
            self.coolant_pressure_bar = 2.1
            self.vibration_g = 0.28
        elif self.profile == "door_seal_breach":
            self.door_seal_ok = False
            self.humidity_pct = 45.0
        elif self.profile == "power_failure":
            self.power_ok = False
            self.compressor_ok = False
            self.coolant_pressure_bar = 0.0
            self.vibration_g = 0.0
        elif self.profile == "sensor_drift":
            self.temp_sensor_ok = False

    def step(self, dt_hours: float):
        """Advances physics engine dynamics using deterministic thermodynamic models."""
        if self.profile == "nominal":
            # Small standard noise matching nominal operations
            self.actual_temp_c = self.target_temp + (0.1 * dt_hours)
            self.temp_c = self.actual_temp_c
            self.humidity_pct = max(10.0, min(20.0, self.humidity_pct + 0.1 * dt_hours))
            self.coolant_pressure_bar = 12.0 + (0.05 * dt_hours)
            self.vibration_g = 0.05
            
        elif self.profile == "compressor_failure":
            # Continuous warming at 0.8°C / hour
            self.actual_temp_c += 0.8 * dt_hours
            self.temp_c = self.actual_temp_c
            self.coolant_pressure_bar = max(1.0, self.coolant_pressure_bar - 0.2 * dt_hours)
            self.vibration_g = min(0.5, self.vibration_g + 0.01 * dt_hours)
            
        elif self.profile == "door_seal_breach":
            # Convective warm air ingress causes moderate thermal drift and high moisture
            self.actual_temp_c += 0.3 * dt_hours
            self.temp_c = self.actual_temp_c
            self.humidity_pct = min(95.0, self.humidity_pct + 8.5 * dt_hours)
            if self.humidity_pct > 60.0:
                self.door_open_count = int(self.humidity_pct / 10)
                
        elif self.profile == "power_failure":
            # Complete system shutdown brings temperature toward ambient rapidly at 2.0°C / hour
            if self.actual_temp_c < self.ambient_temp:
                self.actual_temp_c += 2.0 * dt_hours
            self.temp_c = self.actual_temp_c
            self.coolant_pressure_bar = max(0.0, self.coolant_pressure_bar - 3.0 * dt_hours)
            self.vibration_g = 0.0
            
        elif self.profile == "sensor_drift":
            # Core sensor reports safe levels while actual internal physics degrades severely
            self.actual_temp_c += 1.1 * dt_hours
            self.temp_c = self.target_temp + 0.2  # Locked display anomaly

    def status_label(self) -> str:
        """State machine evaluating active operational exceptions and compliance thresholds."""
        if not self.power_ok:
            return "POWER_LOSS"
        if not self.temp_sensor_ok:
            return "SENSOR_FAULT"
        if not self.compressor_ok:
            return "COMPRESSOR_FAIL"
        if not self.door_seal_ok:
            return "DOOR_BREACH"
        
        # Evaluate standard WHO storage thresholds relative to targets
        temp_delta = self.temp_c - self.target_temp
        if temp_delta > 12.0:
            return "TEMP_EXCURSION"
        if temp_delta > 8.0:
            return "TEMP_CRITICAL"
        if temp_delta > 5.0:
            return "TEMP_WARNING"
            
        return "NOMINAL"

    def snapshot(self, timestamp: datetime) -> Dict[str, Any]:
        return {
            "timestamp": timestamp.isoformat(),
            "equipment_id": self.equipment_id,
            "equipment_type": "PharmaFreezer",
            "profile": self.profile,
            "site_id": self.site_id,
            "product_type": self.product_type,
            "temp_c": round(self.temp_c, 2),
            "actual_temp_c": round(self.actual_temp_c, 2),
            "humidity_pct": round(self.humidity_pct, 2),
            "compressor_ok": self.compressor_ok,
            "door_seal_ok": self.door_seal_ok,
            "door_open_count": self.door_open_count,
            "power_ok": self.power_ok,
            "temp_sensor_ok": self.temp_sensor_ok,
            "vibration_g": round(self.vibration_g, 3),
            "coolant_pressure_bar": round(self.coolant_pressure_bar, 2),
            "product_count": self.product_count,
            "status": self.status_label()
        }


# ==============================================================================
# 2. DrugDispenser Implementation
# ==============================================================================

class DrugDispenser:
    """
    Simulates automated pharmaceutical item inventory distribution systems 
    monitoring environmental constraints (15-25°C) and secure operations.
    """
    def __init__(self, equipment_id: str, profile: str = "nominal", product_type: str = "general_meds", site_id: str = "site_a"):
        self.equipment_id = equipment_id
        self.profile = profile
        self.product_type = product_type
        self.site_id = site_id
        
        # Telemetry fields
        self.temp_c = 19.5
        self.humidity_pct = 40.0
        self.inventory_pct = 88.0
        self.motor_ok = True
        self.access_count_24h = 14
        self.unusual_access = False
        self.last_access_user = "STAFF_RN_04"
        self.dispense_accuracy_pct = 99.8
        
        self._apply_profile_states()

    def _apply_profile_states(self):
        if self.profile == "inventory_low":
            self.inventory_pct = 8.5
        elif self.profile == "access_anomaly":
            self.unusual_access = True
            self.access_count_24h = 85
            self.last_access_user = "UNKNOWN_UID_99"
        elif self.profile == "motor_jam":
            self.motor_ok = False
            self.dispense_accuracy_pct = 42.1
        elif self.profile == "temp_out_of_range":
            self.temp_c = 29.4

    def step(self, dt_hours: float):
        if self.profile == "nominal":
            self.temp_c = 19.5 + (0.05 * dt_hours)
            self.inventory_pct = max(0.0, self.inventory_pct - (0.2 * dt_hours))
            
        elif self.profile == "temp_out_of_range":
            self.temp_c += 1.2 * dt_hours
            self.humidity_pct = min(80.0, self.humidity_pct + 1.0 * dt_hours)
            
        elif self.profile == "inventory_low":
            self.inventory_pct = max(1.0, self.inventory_pct - (0.05 * dt_hours))
            
        elif self.profile == "motor_jam":
            self.dispense_accuracy_pct = max(10.0, self.dispense_accuracy_pct - 5.0 * dt_hours)
            
        elif self.profile == "access_anomaly":
            self.access_count_24h += int(4 * dt_hours)

    def status_label(self) -> str:
        if self.unusual_access:
            return "ACCESS_ANOMALY"
        if not self.motor_ok:
            return "MOTOR_JAM"
        if self.temp_c < 15.0 or self.temp_c > 25.0:
            return "TEMP_ALERT"
        if self.inventory_pct < 10.0:
            return "INVENTORY_LOW"
        return "NOMINAL"

    def snapshot(self, timestamp: datetime) -> Dict[str, Any]:
        return {
            "timestamp": timestamp.isoformat(),
            "equipment_id": self.equipment_id,
            "equipment_type": "DrugDispenser",
            "profile": self.profile,
            "site_id": self.site_id,
            "product_type": self.product_type,
            "temp_c": round(self.temp_c, 2),
            "humidity_pct": round(self.humidity_pct, 2),
            "inventory_pct": round(self.inventory_pct, 1),
            "motor_ok": self.motor_ok,
            "access_count_24h": self.access_count_24h,
            "unusual_access": self.unusual_access,
            "last_access_user": self.last_access_user,
            "dispense_accuracy_pct": round(self.dispense_accuracy_pct, 2),
            "status": self.status_label()
        }


# ==============================================================================
# 3. BloodStorage Implementation
# ==============================================================================

class BloodStorage:
    """
    Simulates specialized critical blood bank refrigeration vaults demanding strict 
    compliance management across biological and kinetic factors (1-6°C threshold).
    """
    def __init__(self, equipment_id: str, profile: str = "nominal", product_type: str = "blood_bank", site_id: str = "site_a"):
        self.equipment_id = equipment_id
        self.profile = profile
        self.product_type = product_type
        self.site_id = site_id
        
        # Telemetry fields
        self.temp_c = 4.0
        self.units_total = 340
        self.units_expiring_48h = 0
        self.contamination_risk_pct = 0.02
        self.door_seal_ok = True
        self.co2_ppm = 380.0
        self.agitation_g = 0.12  # Active operational rocking monitor threshold
        
        self._apply_profile_states()

    def _apply_profile_states(self):
        if self.profile == "temp_excursion":
            self.temp_c = 9.8
        elif self.profile == "unit_expiry":
            self.units_expiring_48h = 45
        elif self.profile == "contamination_risk":
            self.co2_ppm = 1150.0
            self.contamination_risk_pct = 15.4
        elif self.profile == "seal_breach":
            self.door_seal_ok = False
            self.co2_ppm = 650.0

    def step(self, dt_hours: float):
        if self.profile == "nominal":
            self.temp_c = 4.0 + (0.02 * dt_hours)
            self.co2_ppm = max(350.0, min(420.0, self.co2_ppm + 0.2 * dt_hours))
            
        elif self.profile == "temp_excursion":
            self.temp_c += 0.9 * dt_hours
            self.contamination_risk_pct = min(100.0, self.contamination_risk_pct + 1.5 * dt_hours)
            
        elif self.profile == "contamination_risk":
            self.co2_ppm += 45.0 * dt_hours
            self.contamination_risk_pct = min(100.0, self.contamination_risk_pct + 3.2 * dt_hours)
            
        elif self.profile == "seal_breach":
            self.temp_c += 0.4 * dt_hours
            self.co2_ppm = min(2000.0, self.co2_ppm + 12.0 * dt_hours)
            
        elif self.profile == "unit_expiry":
            # Baseline parameters remain steady while biological timestamps shift
            self.temp_c = 4.1

    def status_label(self) -> str:
        if self.temp_c < 1.0 or self.temp_c > 6.0:
            return "TEMP_EXCURSION"
        if self.contamination_risk_pct > 10.0 or self.co2_ppm > 1000.0:
            return "CONTAMINATION_RISK"
        if self.units_expiring_48h > 0:
            return "EXPIRY_ALERT"
        return "NOMINAL"

    def snapshot(self, timestamp: datetime) -> Dict[str, Any]:
        return {
            "timestamp": timestamp.isoformat(),
            "equipment_id": self.equipment_id,
            "equipment_type": "BloodStorage",
            "profile": self.profile,
            "site_id": self.site_id,
            "product_type": self.product_type,
            "temp_c": round(self.temp_c, 2),
            "units_total": self.units_total,
            "units_expiring_48h": self.units_expiring_48h,
            "contamination_risk_pct": round(self.contamination_risk_pct, 2),
            "door_seal_ok": self.door_seal_ok,
            "co2_ppm": round(self.co2_ppm, 1),
            "agitation_g": round(self.agitation_g, 3),
            "status": self.status_label()
        }


# ==============================================================================
# 4. Fleet Mock Database Generation
# ==============================================================================

def mock_db() -> Dict[str, List[Any]]:
    """Generates structured fleet tracking collections mapped exactly across requested facilities."""
    return {
        "pharma_freezers": [
            PharmaFreezer("FZ-01", "compressor_failure", "vaccine_storage", "site_a"),
            PharmaFreezer("FZ-02", "door_seal_breach", "insulin_storage", "site_a"),
            PharmaFreezer("FZ-03", "nominal", "blood_plasma", "site_b"),
            PharmaFreezer("FZ-04", "power_failure", "vaccine_storage", "site_b"),
            PharmaFreezer("FZ-05", "sensor_drift", "general_meds", "site_c")
        ],
        "drug_dispensers": [
            DrugDispenser("DD-01", "access_anomaly", "controlled_substances", "site_a"),
            DrugDispenser("DD-02", "inventory_low", "general_meds", "site_b"),
            DrugDispenser("DD-03", "motor_jam", "oncology_meds", "site_c")
        ],
        "blood_storage": [
            BloodStorage("BS-01", "temp_excursion", "blood_bank", "site_a"),
            BloodStorage("BS-02", "unit_expiry", "blood_bank", "site_b"),
            BloodStorage("BS-03", "nominal", "blood_bank", "site_c")
        ]
    }


# ==============================================================================
# 5. Advanced Analytical Failure Prediction
# ==============================================================================

def predict_failure(appliance_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates real-time telemetry inputs to predict remaining useful life (RUL) 
    and identify systemic anomalies prior to asset catastrophic failure.
    """
    eq_type = appliance_data.get("equipment_type")
    profile = appliance_data.get("profile", "nominal")
    status = appliance_data.get("status", "NOMINAL")
    
    # Initialize nominal baseline response contract
    result = {
        "predicted_failure": "NONE",
        "confidence": 0.0,
        "root_cause": "All operational telemetry parameters satisfy authorized GxP/WHO baseline tolerances.",
        "time_to_critical_hours": 999.0
    }
    
    if profile == "nominal" and status == "NOMINAL":
        return result

    # --- Processing Rules: PharmaFreezer ---
    if eq_type == "PharmaFreezer":
        current_temp = appliance_data.get("temp_c", -25.0)
        critical_threshold = -13.0 # WHO boundary limit deviation trigger
        
        if profile == "compressor_failure" or status == "COMPRESSOR_FAIL":
            warming_rate = 0.8
            remaining_hours = max(0.0, (critical_threshold - current_temp) / warming_rate)
            return {
                "predicted_failure": "COMPRESSOR_MECHANICAL_COLLAPSE",
                "confidence": 0.95,
                "root_cause": "Coolant system structural pressure drop detected below critical threshold boundaries.",
                "time_to_critical_hours": round(remaining_hours, 1)
            }
            
        elif profile == "power_failure" or status == "POWER_LOSS":
            warming_rate = 2.0
            remaining_hours = max(0.0, (critical_threshold - current_temp) / warming_rate)
            return {
                "predicted_failure": "TOTAL_POWER_VACUUM",
                "confidence": 0.98,
                "root_cause": "Primary facility power source input completely terminated. Main breaker override recommended.",
                "time_to_critical_hours": round(remaining_hours, 1)
            }
            
        elif profile == "door_seal_breach" or status == "DOOR_BREACH":
            return {
                "predicted_failure": "THERMAL_INSULATION_EFFICIENCY_BREACH",
                "confidence": 0.88,
                "root_cause": "Continuous convective heat and moisture ingress originating from degraded structural chassis door gasket.",
                "time_to_critical_hours": 18.5
            }
            
        elif profile == "sensor_drift" or status == "SENSOR_FAULT":
            return {
                "predicted_failure": "CRITICAL_SENSOR_LOGIC_DEVIATION",
                "confidence": 0.92,
                "root_cause": "Internal tracking telemetry display frozen. Actual physical internal temperature is climbing silently.",
                "time_to_critical_hours": 4.0
            }

    # --- Processing Rules: DrugDispenser ---
    elif eq_type == "DrugDispenser":
        if profile == "access_anomaly" or status == "ACCESS_ANOMALY":
            return {
                "predicted_failure": "COMPLIANCE_SECURITY_COMPROMISE",
                "confidence": 0.96,
                "root_cause": "High-frequency out-of-schedule authentication challenges observed using unknown staff IDs.",
                "time_to_critical_hours": 0.0  # Immediate enforcement action required
            }
        elif profile == "inventory_low" or status == "INVENTORY_LOW":
            return {
                "predicted_failure": "STOCKOUT_DEPLETION_EVENT",
                "confidence": 0.90,
                "root_cause": "Active product volume inventory drops below standard 10% reserve threshold configuration limits.",
                "time_to_critical_hours": 12.0
            }
        elif profile == "motor_jam" or status == "MOTOR_JAM":
            return {
                "predicted_failure": "MECHANICAL_ACTUATOR_STALL",
                "confidence": 0.85,
                "root_cause": "Dispensation accuracy collapse caused by physical drivetrain mechanical blockage.",
                "time_to_critical_hours": 2.5
            }
        elif profile == "temp_out_of_range" or status == "TEMP_ALERT":
            return {
                "predicted_failure": "CONTROLLED_ROOM_TEMP_EXCURSION",
                "confidence": 0.94,
                "root_cause": "Chassis thermal systems tracking parameters drift significantly higher than authorized 25°C boundaries.",
                "time_to_critical_hours": 6.5
            }

    # --- Processing Rules: BloodStorage ---
    elif eq_type == "BloodStorage":
        if profile == "temp_excursion" or status == "TEMP_EXCURSION":
            return {
                "predicted_failure": "BIOLOGICAL_ASSET_SPOILAGE",
                "confidence": 0.97,
                "root_cause": "Refrigeration threshold parameters exceeding critical 6.0°C regulatory guidelines.",
                "time_to_critical_hours": 1.2
            }
        elif profile == "unit_expiry" or status == "EXPIRY_ALERT":
            return {
                "predicted_failure": "REGULATORY_SHELF_LIFE_EXPIRATION",
                "confidence": 0.95,
                "root_cause": "Substantial quantity of biological whole blood units approaching internal 42-day lifespan tracking limits.",
                "time_to_critical_hours": 48.0
            }
        elif profile == "contamination_risk" or status == "CONTAMINATION_RISK":
            return {
                "predicted_failure": "BIOLOGICAL_CONTAMINATION_EVENT",
                "confidence": 0.89,
                "root_cause": "Internal air sample telemetry reveals elevated metabolic CO2 levels pointing to seal decay or organic activity.",
                "time_to_critical_hours": 8.0
            }
        elif profile == "seal_breach":
            return {
                "predicted_failure": "ENVIRONMENTAL_CONTAINMENT_LOSS",
                "confidence": 0.86,
                "root_cause": "Degraded main access panel gasket letting outside ambient air drift inside slowly.",
                "time_to_critical_hours": 14.0
            }

    return result


# ==============================================================================
# Execution Runtime Context Validation Verification Block
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("PharmaSense AI — Core Physics Simulation Engine Verification")
    print("=" * 80)
    
    # Initialize database
    fleet = mock_db()
    simulation_duration_hours = 8.0
    
    print(f"\nAdvancing all simulation layers forward by {simulation_duration_hours} hours sequentially...\n")
    
    # Cycle targets through execution steps
    for categorization, appliances in fleet.items():
        print(f"\n>> Category: {categorization.upper()}")
        print("-" * 80)
        
        for item in appliances:
            # Advance structural time steps
            item.step(simulation_duration_hours)
            
            # Fetch active snapshot matrix state
            data_snapshot = item.snapshot(datetime.now())
            prediction_matrix = predict_failure(data_snapshot)
            
            print(f"Asset ID: {data_snapshot['equipment_id']} | Profile: {data_snapshot['profile']:<18} | Site: {data_snapshot['site_id']}")
            print(f"  Reported Temp : {data_snapshot['temp_c']}°C (Actual Physics: {data_snapshot.get('actual_temp_c', data_snapshot['temp_c'])}°C)")
            print(f"  Evaluated Status: {data_snapshot['status']}")
            
            if prediction_matrix["predicted_failure"] != "NONE":
                print(f"  [WARN] Prediction   : {prediction_matrix['predicted_failure']}")
                print(f"     Confidence   : {prediction_matrix['confidence']:.0%}")
                print(f"     Time to Crit : {prediction_matrix['time_to_critical_hours']} hours")
                print(f"     Root Cause   : {prediction_matrix['root_cause']}")
            print()
