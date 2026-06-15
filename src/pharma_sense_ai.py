#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import math
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum


class EquipmentStatus(Enum):
    """Status labels for equipment state machine."""
    # PharmaFreezer
    NOMINAL = "NOMINAL"
    TEMP_WARNING = "TEMP_WARNING"
    TEMP_CRITICAL = "TEMP_CRITICAL"
    TEMP_EXCURSION = "TEMP_EXCURSION"
    SENSOR_FAULT = "SENSOR_FAULT"
    POWER_LOSS = "POWER_LOSS"
    DOOR_BREACH = "DOOR_BREACH"
    COMPRESSOR_FAIL = "COMPRESSOR_FAIL"
    
    # DrugDispenser
    INVENTORY_LOW = "INVENTORY_LOW"
    ACCESS_ANOMALY = "ACCESS_ANOMALY"
    MOTOR_JAM = "MOTOR_JAM"
    TEMP_ALERT = "TEMP_ALERT"
    
    # BloodStorage
    EXPIRY_ALERT = "EXPIRY_ALERT"
    CONTAMINATION_RISK = "CONTAMINATION_RISK"


class PharmaFreezer:
    """
    Pharmaceutical freezer simulator with failure profiles.
    
    Maintains vaccine, insulin, and general medication storage at -20°C to -80°C.
    Simulates compressor failures, door seal breaches, power loss, sensor drift, and vibration.
    """
    
    AMBIENT_TEMP_C = 22.0  # Room temperature
    OPTIMAL_TEMP_C = -20.0
    
    def __init__(
        self,
        equipment_id: str,
        profile: str = "nominal",
        product_type: str = "vaccine_storage",
        site_name: str = "site_a"
    ):
        """
        Initialize a PharmaFreezer.
        
        Args:
            equipment_id: Unique identifier (e.g., "FZ-01")
            profile: Failure profile - nominal, compressor_failure, door_seal_breach, power_failure, sensor_drift
            product_type: Type of product stored
            site_name: Site location
        """
        self.equipment_id = equipment_id
        self.profile = profile
        self.product_type = product_type
        self.site_name = site_name
        
        # State variables
        self.temp_c = self.OPTIMAL_TEMP_C
        self.humidity_pct = 35.0
        self.compressor_ok = True
        self.door_seal_ok = True
        self.door_open_count = 0
        self.power_ok = True
        self.temp_sensor_ok = True
        self.actual_temp_c = self.OPTIMAL_TEMP_C  # True temp when sensor drifts
        self.vibration_g = 0.1  # Acceleration in g-force
        self.coolant_pressure_bar = 8.5
        self.product_count = 500
        self.runtime_hours = 0.0
        
        # Initialize failure profile
        self._apply_profile()
    
    def _apply_profile(self):
        """Apply initial conditions for the failure profile."""
        if self.profile == "compressor_failure":
            self.compressor_ok = False
            self.coolant_pressure_bar = 2.1
        elif self.profile == "door_seal_breach":
            self.door_seal_ok = False
            self.humidity_pct = 65.0
        elif self.profile == "power_failure":
            self.power_ok = False
        elif self.profile == "sensor_drift":
            self.temp_sensor_ok = False
    
    def step(self, dt_hours: float) -> None:
        """
        Advance simulation by dt_hours with physics calculations.
        
        Args:
            dt_hours: Time step in hours
        """
        self.runtime_hours += dt_hours
        
        # Compressor failure: controlled temperature rise at 0.8°C/hour
        if not self.compressor_ok:
            self.temp_c += 0.8 * dt_hours
        
        # Power failure: faster temperature rise at 2°C/hour
        if not self.power_ok:
            self.temp_c += 2.0 * dt_hours
        
        # Door seal breach: humidity increases, slight temperature rise
        if not self.door_seal_ok:
            self.humidity_pct = min(95.0, self.humidity_pct + 2.0 * dt_hours)
            # Sealed breach allows warm air ingress
            self.temp_c += 0.3 * dt_hours
        
        # Sensor drift: actual temp climbs but displayed temp stays nominal
        if not self.temp_sensor_ok:
            self.actual_temp_c += 0.5 * dt_hours
        
        # Normal operation: coolant pressure cycles
        if self.power_ok and self.compressor_ok:
            self.vibration_g = 0.1 + 0.05 * math.sin(2 * math.pi * self.runtime_hours / 0.5)
            self.coolant_pressure_bar = 8.5 + 0.3 * math.sin(2 * math.pi * self.runtime_hours / 2.0)
        else:
            self.vibration_g = 0.05
            self.coolant_pressure_bar = max(0.5, self.coolant_pressure_bar - 0.1 * dt_hours)
    
    def snapshot(self, timestamp: datetime) -> Dict[str, Any]:
        """
        Return a flat dictionary snapshot of equipment state.
        
        Args:
            timestamp: Snapshot timestamp
            
        Returns:
            Dictionary with all state variables
        """
        return {
            "equipment_id": self.equipment_id,
            "equipment_type": "PharmaFreezer",
            "profile": self.profile,
            "product_type": self.product_type,
            "site_name": self.site_name,
            "timestamp": timestamp.isoformat(),
            "temp_c": round(self.temp_c, 2),
            "humidity_pct": round(self.humidity_pct, 2),
            "compressor_ok": self.compressor_ok,
            "door_seal_ok": self.door_seal_ok,
            "door_open_count": self.door_open_count,
            "power_ok": self.power_ok,
            "temp_sensor_ok": self.temp_sensor_ok,
            "actual_temp_c": round(self.actual_temp_c, 2),
            "vibration_g": round(self.vibration_g, 3),
            "coolant_pressure_bar": round(self.coolant_pressure_bar, 2),
            "product_count": self.product_count,
            "status": self.status_label(),
            "runtime_hours": round(self.runtime_hours, 2),
        }
    
    def status_label(self) -> str:
        """
        State machine that returns current equipment status.
        
        Returns:
            Status label string
        """
        # Check sensor fault first
        if not self.temp_sensor_ok and self.actual_temp_c > -15.0:
            return EquipmentStatus.SENSOR_FAULT.value
        
        # Check power loss
        if not self.power_ok:
            return EquipmentStatus.POWER_LOSS.value
        
        # Check compressor failure
        if not self.compressor_ok:
            return EquipmentStatus.COMPRESSOR_FAIL.value
        
        # Check door breach
        if not self.door_seal_ok:
            return EquipmentStatus.DOOR_BREACH.value
        
        # Check temperature thresholds (display temp or actual if sensor drifts)
        display_temp = self.actual_temp_c if not self.temp_sensor_ok else self.temp_c
        
        if display_temp > -12.0:
            return EquipmentStatus.TEMP_EXCURSION.value
        elif display_temp > -16.0:
            return EquipmentStatus.TEMP_CRITICAL.value
        elif display_temp >= -18.0:
            return EquipmentStatus.TEMP_WARNING.value
        
        return EquipmentStatus.NOMINAL.value


class DrugDispenser:
    """
    Automated drug dispensing system with inventory and access control.
    
    Maintains controlled substances at 15-25°C with access logging and
    motor-driven dispensing mechanisms.
    """
    
    OPTIMAL_TEMP_C = 20.0
    TEMP_MIN = 15.0
    TEMP_MAX = 25.0
    
    def __init__(
        self,
        equipment_id: str,
        profile: str = "nominal",
        drug_class: str = "general_meds",
        site_name: str = "site_a"
    ):
        """
        Initialize a DrugDispenser.
        
        Args:
            equipment_id: Unique identifier (e.g., "DD-01")
            profile: Failure profile - nominal, inventory_low, access_anomaly, motor_jam, temp_out_of_range
            drug_class: Type of drugs stored
            site_name: Site location
        """
        self.equipment_id = equipment_id
        self.profile = profile
        self.drug_class = drug_class
        self.site_name = site_name
        
        # State variables
        self.temp_c = self.OPTIMAL_TEMP_C
        self.humidity_pct = 45.0
        self.inventory_pct = 85.0
        self.motor_ok = True
        self.access_count_24h = 12
        self.unusual_access = False
        self.last_access_user = "pharm_tech_01"
        self.dispense_accuracy_pct = 99.5
        self.runtime_hours = 0.0
        
        # Initialize failure profile
        self._apply_profile()
    
    def _apply_profile(self):
        """Apply initial conditions for the failure profile."""
        if self.profile == "inventory_low":
            self.inventory_pct = 15.0
        elif self.profile == "access_anomaly":
            self.access_count_24h = 45  # Abnormal access pattern
            self.unusual_access = True
        elif self.profile == "motor_jam":
            self.motor_ok = False
            self.dispense_accuracy_pct = 45.0
        elif self.profile == "temp_out_of_range":
            self.temp_c = 27.5
    
    def step(self, dt_hours: float) -> None:
        """
        Advance simulation by dt_hours with physics calculations.
        
        Args:
            dt_hours: Time step in hours
        """
        self.runtime_hours += dt_hours
        
        # Temperature regulation (PI controller behavior)
        if self.temp_c > self.TEMP_MAX:
            # Cooling needed
            temp_error = self.temp_c - self.TEMP_MAX
            self.temp_c -= 0.5 * temp_error * dt_hours
        elif self.temp_c < self.TEMP_MIN:
            # Heating needed
            temp_error = self.TEMP_MIN - self.temp_c
            self.temp_c += 0.3 * temp_error * dt_hours
        
        # Inventory depletion (normal use or motor jam prevents restocking)
        if self.motor_ok:
            # Slow natural depletion during operation hours
            self.inventory_pct = max(0.0, self.inventory_pct - 0.5 * dt_hours)
        else:
            # Motor jam means no restocking, inventory stays constant
            pass
        
        # Anomalous access gradually increases (intrusion attempt simulation)
        if self.unusual_access:
            self.access_count_24h = min(100, self.access_count_24h + 2.0 * dt_hours)
        
        # Motor jam increases dispense inaccuracy
        if not self.motor_ok:
            self.dispense_accuracy_pct = max(10.0, self.dispense_accuracy_pct - 1.0 * dt_hours)
    
    def snapshot(self, timestamp: datetime) -> Dict[str, Any]:
        """
        Return a flat dictionary snapshot of equipment state.
        
        Args:
            timestamp: Snapshot timestamp
            
        Returns:
            Dictionary with all state variables
        """
        return {
            "equipment_id": self.equipment_id,
            "equipment_type": "DrugDispenser",
            "profile": self.profile,
            "drug_class": self.drug_class,
            "site_name": self.site_name,
            "timestamp": timestamp.isoformat(),
            "temp_c": round(self.temp_c, 2),
            "humidity_pct": round(self.humidity_pct, 2),
            "inventory_pct": round(self.inventory_pct, 2),
            "motor_ok": self.motor_ok,
            "access_count_24h": self.access_count_24h,
            "unusual_access": self.unusual_access,
            "last_access_user": self.last_access_user,
            "dispense_accuracy_pct": round(self.dispense_accuracy_pct, 2),
            "status": self.status_label(),
            "runtime_hours": round(self.runtime_hours, 2),
        }
    
    def status_label(self) -> str:
        """
        State machine that returns current equipment status.
        
        Returns:
            Status label string
        """
        # Check temperature out of range (highest priority)
        if self.temp_c < self.TEMP_MIN or self.temp_c > self.TEMP_MAX:
            return EquipmentStatus.TEMP_ALERT.value
        
        # Check motor jam
        if not self.motor_ok:
            return EquipmentStatus.MOTOR_JAM.value
        
        # Check access anomaly
        if self.unusual_access or self.access_count_24h > 30:
            return EquipmentStatus.ACCESS_ANOMALY.value
        
        # Check inventory
        if self.inventory_pct < 20.0:
            return EquipmentStatus.INVENTORY_LOW.value
        
        return EquipmentStatus.NOMINAL.value


class BloodStorage:
    """
    Blood bank storage system for maintaining blood units at 1-6°C.
    
    Tracks unit expiry (42-day shelf life), contamination risk, agitation, and
    door seal integrity.
    """
    
    OPTIMAL_TEMP_C = 4.0
    TEMP_MIN = 1.0
    TEMP_MAX = 6.0
    UNIT_SHELF_LIFE_DAYS = 42
    
    def __init__(
        self,
        equipment_id: str,
        profile: str = "nominal",
        facility: str = "blood_bank",
        site_name: str = "site_a"
    ):
        """
        Initialize a BloodStorage unit.
        
        Args:
            equipment_id: Unique identifier (e.g., "BS-01")
            profile: Failure profile - nominal, temp_excursion, unit_expiry, contamination_risk, seal_breach
            facility: Type of blood bank
            site_name: Site location
        """
        self.equipment_id = equipment_id
        self.profile = profile
        self.facility = facility
        self.site_name = site_name
        
        # State variables
        self.temp_c = self.OPTIMAL_TEMP_C
        self.units_total = 200
        self.units_expiring_48h = 0
        self.contamination_risk_pct = 2.0
        self.door_seal_ok = True
        self.co2_ppm = 400.0  # CO2 concentration (contamination indicator)
        self.agitation_g = 0.0  # Movement/vibration
        self.runtime_hours = 0.0
        self.creation_time = datetime.now()
        
        # Initialize failure profile
        self._apply_profile()
    
    def _apply_profile(self):
        """Apply initial conditions for the failure profile."""
        if self.profile == "temp_excursion":
            self.temp_c = 8.5
        elif self.profile == "unit_expiry":
            # Simulate units stored for 40 days already
            self.units_expiring_48h = 45
        elif self.profile == "contamination_risk":
            self.contamination_risk_pct = 25.0
            self.co2_ppm = 2800.0
        elif self.profile == "seal_breach":
            self.door_seal_ok = False
    
    def step(self, dt_hours: float) -> None:
        """
        Advance simulation by dt_hours with physics calculations.
        
        Args:
            dt_hours: Time step in hours
        """
        self.runtime_hours += dt_hours
        
        # Temperature regulation
        if self.temp_c > self.TEMP_MAX:
            temp_error = self.temp_c - self.TEMP_MAX
            self.temp_c -= 0.4 * temp_error * dt_hours
        elif self.temp_c < self.TEMP_MIN:
            temp_error = self.TEMP_MIN - self.temp_c
            self.temp_c += 0.3 * temp_error * dt_hours
        
        # Door seal breach allows temperature rise and contamination
        if not self.door_seal_ok:
            self.temp_c += 0.2 * dt_hours
            self.co2_ppm = min(5000.0, self.co2_ppm + 20.0 * dt_hours)
            self.contamination_risk_pct = min(95.0, self.contamination_risk_pct + 0.5 * dt_hours)
        
        # CO2 buildup increases contamination risk
        if self.co2_ppm > 1000.0:
            self.contamination_risk_pct = min(
                95.0,
                self.contamination_risk_pct + 0.1 * (self.co2_ppm / 1000.0 - 1.0) * dt_hours
            )
        
        # Expiry calculation: units approaching 42-day shelf life
        days_stored = (datetime.now() - self.creation_time).total_seconds() / (24 * 3600)
        units_at_risk = max(0, int(self.units_total * (days_stored / self.UNIT_SHELF_LIFE_DAYS)))
        self.units_expiring_48h = min(self.units_total, units_at_risk)
        
        # Agitation (normal operation creates minimal vibration)
        self.agitation_g = 0.05 + 0.02 * math.sin(2 * math.pi * self.runtime_hours / 3.0)
    
    def snapshot(self, timestamp: datetime) -> Dict[str, Any]:
        """
        Return a flat dictionary snapshot of equipment state.
        
        Args:
            timestamp: Snapshot timestamp
            
        Returns:
            Dictionary with all state variables
        """
        return {
            "equipment_id": self.equipment_id,
            "equipment_type": "BloodStorage",
            "profile": self.profile,
            "facility": self.facility,
            "site_name": self.site_name,
            "timestamp": timestamp.isoformat(),
            "temp_c": round(self.temp_c, 2),
            "units_total": self.units_total,
            "units_expiring_48h": self.units_expiring_48h,
            "contamination_risk_pct": round(self.contamination_risk_pct, 2),
            "door_seal_ok": self.door_seal_ok,
            "co2_ppm": round(self.co2_ppm, 1),
            "agitation_g": round(self.agitation_g, 3),
            "status": self.status_label(),
            "runtime_hours": round(self.runtime_hours, 2),
        }
    
    def status_label(self) -> str:
        """
        State machine that returns current equipment status.
        
        Returns:
            Status label string
        """
        # Check contamination risk first (highest priority for blood safety)
        if self.contamination_risk_pct > 20.0 or self.co2_ppm > 2000.0:
            return EquipmentStatus.CONTAMINATION_RISK.value
        
        # Check temperature excursion
        if self.temp_c < self.TEMP_MIN or self.temp_c > self.TEMP_MAX:
            return EquipmentStatus.TEMP_EXCURSION.value
        
        # Check expiry alert
        if self.units_expiring_48h > 30:
            return EquipmentStatus.EXPIRY_ALERT.value
        
        return EquipmentStatus.NOMINAL.value


def mock_db() -> Dict[str, Any]:
    """
    Create a mock database of pharmaceutical equipment across multiple sites.
    
    Returns:
        Dictionary with equipment lists organized by type
    """
    equipment_db = {
        "pharma_freezers": [
            PharmaFreezer("FZ-01", profile="compressor_failure", product_type="vaccine_storage", site_name="site_a"),
            PharmaFreezer("FZ-02", profile="door_seal_breach", product_type="insulin_storage", site_name="site_a"),
            PharmaFreezer("FZ-03", profile="nominal", product_type="blood_plasma", site_name="site_b"),
            PharmaFreezer("FZ-04", profile="power_failure", product_type="vaccine_storage", site_name="site_b"),
            PharmaFreezer("FZ-05", profile="sensor_drift", product_type="general_meds", site_name="site_c"),
        ],
        "drug_dispensers": [
            DrugDispenser("DD-01", profile="access_anomaly", drug_class="controlled_substances", site_name="site_a"),
            DrugDispenser("DD-02", profile="inventory_low", drug_class="general_meds", site_name="site_b"),
            DrugDispenser("DD-03", profile="motor_jam", drug_class="oncology_meds", site_name="site_c"),
        ],
        "blood_storage": [
            BloodStorage("BS-01", profile="temp_excursion", facility="blood_bank", site_name="site_a"),
            BloodStorage("BS-02", profile="unit_expiry", facility="blood_bank", site_name="site_b"),
            BloodStorage("BS-03", profile="nominal", facility="blood_bank", site_name="site_c"),
        ],
    }
    
    return equipment_db


def predict_failure(appliance_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Predict equipment failure based on current telemetry data.
    
    Uses heuristic rules correlated to equipment state to predict failures
    with confidence scores and time-to-critical estimates.
    
    Args:
        appliance_data: Snapshot dictionary from equipment.snapshot()
        
    Returns:
        Dictionary with predicted_failure, confidence, root_cause, time_to_critical_hours
    """
    eq_type = appliance_data.get("equipment_type", "Unknown")
    temp = appliance_data.get("temp_c", 20.0)
    status = appliance_data.get("status", "NOMINAL")
    
    prediction = {
        "predicted_failure": "NONE",
        "confidence": 0.0,
        "root_cause": "No anomalies detected",
        "time_to_critical_hours": float("inf"),
    }
    
    # PharmaFreezer predictions
    if eq_type == "PharmaFreezer":
        compressor_ok = appliance_data.get("compressor_ok", True)
        door_seal_ok = appliance_data.get("door_seal_ok", True)
        power_ok = appliance_data.get("power_ok", True)
        temp_sensor_ok = appliance_data.get("temp_sensor_ok", True)
        coolant_pressure = appliance_data.get("coolant_pressure_bar", 8.5)
        vibration = appliance_data.get("vibration_g", 0.1)
        
        # Compressor failure detection
        if not compressor_ok or (coolant_pressure < 3.0 and power_ok):
            prediction["predicted_failure"] = "COMPRESSOR_FAILURE"
            prediction["confidence"] = 0.95
            prediction["root_cause"] = "Compressor not operational or low coolant pressure"
            # From -20°C to ambient at 0.8°C/hour = ~52.5 hours to reach 22°C
            prediction["time_to_critical_hours"] = max(0.5, (22.0 - temp) / 0.8)
        
        # Power failure detection
        elif not power_ok:
            prediction["predicted_failure"] = "POWER_FAILURE"
            prediction["confidence"] = 0.98
            prediction["root_cause"] = "Unit lost power supply"
            # From -20°C at 2°C/hour = 21 hours to ambient
            prediction["time_to_critical_hours"] = max(0.5, (22.0 - temp) / 2.0)
        
        # Door seal breach detection
        elif not door_seal_ok:
            prediction["predicted_failure"] = "DOOR_SEAL_BREACH"
            prediction["confidence"] = 0.85
            prediction["root_cause"] = "Door seal compromised, warm air ingress"
            # Slower rise at 0.3°C/hour
            prediction["time_to_critical_hours"] = max(2.0, (22.0 - temp) / 0.3)
        
        # Sensor drift detection
        elif not temp_sensor_ok:
            prediction["predicted_failure"] = "SENSOR_DRIFT"
            prediction["confidence"] = 0.80
            prediction["root_cause"] = "Temperature sensor reading error, actual temp drifting"
            prediction["time_to_critical_hours"] = 12.0
        
        # Temperature trend warning
        elif temp > -16.0:
            prediction["predicted_failure"] = "TEMPERATURE_EXCURSION_TREND"
            prediction["confidence"] = 0.70
            prediction["root_cause"] = "Temperature rising, may indicate imminent compressor or cooling failure"
            prediction["time_to_critical_hours"] = 8.0
    
    # DrugDispenser predictions
    elif eq_type == "DrugDispenser":
        motor_ok = appliance_data.get("motor_ok", True)
        inventory = appliance_data.get("inventory_pct", 50.0)
        access_count = appliance_data.get("access_count_24h", 12)
        unusual_access = appliance_data.get("unusual_access", False)
        accuracy = appliance_data.get("dispense_accuracy_pct", 99.5)
        
        # Motor jam detection
        if not motor_ok:
            prediction["predicted_failure"] = "MOTOR_JAM"
            prediction["confidence"] = 0.92
            prediction["root_cause"] = "Motor mechanism jammed, cannot dispense drugs"
            prediction["time_to_critical_hours"] = 0.5
        
        # Inventory depletion warning
        elif inventory < 10.0:
            prediction["predicted_failure"] = "INVENTORY_DEPLETED"
            prediction["confidence"] = 0.90
            prediction["root_cause"] = "Drug inventory critically low"
            # At 0.5% per hour, 10% to empty = 20 hours
            prediction["time_to_critical_hours"] = 20.0
        
        # Access anomaly detection
        elif unusual_access or access_count > 40:
            prediction["predicted_failure"] = "ACCESS_ANOMALY_DETECTED"
            prediction["confidence"] = 0.88
            prediction["root_cause"] = "Unusual access pattern indicates potential tampering"
            prediction["time_to_critical_hours"] = 1.0
        
        # Accuracy degradation
        elif accuracy < 85.0:
            prediction["predicted_failure"] = "DISPENSE_ACCURACY_DEGRADED"
            prediction["confidence"] = 0.75
            prediction["root_cause"] = "Dispense accuracy declining, motor mechanism wear"
            prediction["time_to_critical_hours"] = 4.0
    
    # BloodStorage predictions
    elif eq_type == "BloodStorage":
        door_seal_ok = appliance_data.get("door_seal_ok", True)
        units_expiring = appliance_data.get("units_expiring_48h", 0)
        contamination_risk = appliance_data.get("contamination_risk_pct", 2.0)
        co2_ppm = appliance_data.get("co2_ppm", 400.0)
        
        # Contamination risk detection
        if contamination_risk > 30.0 or co2_ppm > 3000.0:
            prediction["predicted_failure"] = "CONTAMINATION_IMMINENT"
            prediction["confidence"] = 0.93
            prediction["root_cause"] = f"High contamination risk ({contamination_risk:.1f}%) or CO2 buildup"
            prediction["time_to_critical_hours"] = 2.0
        
        # Unit expiry warning
        elif units_expiring > 50:
            prediction["predicted_failure"] = "MASS_UNIT_EXPIRY"
            prediction["confidence"] = 0.95
            prediction["root_cause"] = f"{units_expiring} units approaching 42-day shelf life expiry"
            prediction["time_to_critical_hours"] = 48.0
        
        # Door seal breach detection
        elif not door_seal_ok:
            prediction["predicted_failure"] = "DOOR_SEAL_BREACH"
            prediction["confidence"] = 0.89
            prediction["root_cause"] = "Door seal compromised, temperature and contamination risk rising"
            prediction["time_to_critical_hours"] = 6.0
        
        # Temperature excursion
        elif temp < 1.0 or temp > 6.0:
            prediction["predicted_failure"] = "TEMPERATURE_OUT_OF_RANGE"
            prediction["confidence"] = 0.96
            prediction["root_cause"] = "Blood storage temperature outside 1-6°C safe range"
            prediction["time_to_critical_hours"] = 1.0
    
    return prediction


def decide_freezer(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decision tree for PharmaFreezer with WHO temperature standards.
    
    WHO Guidelines:
    - Vaccines: -15°C to -25°C optimal
    - Critical threshold: > 8°C (product damage)
    - Warning threshold: > 5°C for extended periods
    - Sensor drift: Hidden actual temp > 3°C from displayed
    
    Args:
        data: Snapshot dictionary from PharmaFreezer.snapshot()
        
    Returns:
        Decision dictionary with schema: decision_id, analysis, severity, risk_level,
        recoverable, requires_human_approval, approval_message, action_plan
    """
    decision_id = f"DEC-2026-FREEZER-{data.get('equipment_id', 'UNKNOWN')}"
    
    temp_c = data.get("temp_c", -20.0)
    actual_temp = data.get("actual_temp_c", temp_c)
    humidity_pct = data.get("humidity_pct", 35.0)
    power_ok = data.get("power_ok", True)
    compressor_ok = data.get("compressor_ok", True)
    door_seal_ok = data.get("door_seal_ok", True)
    temp_sensor_ok = data.get("temp_sensor_ok", True)
    
    # Initialize decision
    decision = {
        "decision_id": decision_id,
        "analysis": "",
        "severity": 0.0,
        "risk_level": "LOW",
        "recoverable": True,
        "requires_human_approval": False,
        "approval_message": None,
        "action_plan": [],
    }
    
    # --- CRITICAL: Compressor Failure (rising temperature trajectory) ---
    if not compressor_ok:
        decision.update({
            "analysis": f"CRITICAL: Compressor failure detected. Temperature will rise 0.8°C per hour. "
                        f"Current temp {temp_c:.1f}°C. Will reach critical threshold (>8°C) in ~{(8.0 - temp_c) / 0.8:.0f} hours. "
                        "Emergency cooling required immediately.",
            "severity": 0.96,
            "risk_level": "CRITICAL",
            "recoverable": True,
            "requires_human_approval": True,
            "approval_message": "APPROVAL REQUIRED: Authorize compressor replacement or product emergency transfer",
            "action_plan": [
                {
                    "channel": "MAINTENANCE",
                    "action": "EMERGENCY_COMPRESSOR_REPLACEMENT",
                    "params": {
                        "priority": "IMMEDIATE",
                        "estimated_time_to_critical": max(0, (8.0 - temp_c) / 0.8),
                        "max_replacement_hours": 2.0,
                        "backup_cooling": "Stage 2 portable freezer required"
                    }
                },
                {
                    "channel": "SAFETY",
                    "action": "PREPARE_PRODUCT_TRANSFER",
                    "params": {
                        "affected_products": data.get("product_count", 0),
                        "product_type": data.get("product_type", "unknown"),
                        "destination": "Backup freezer or emergency cooler",
                        "transfer_trigger": f"If temp exceeds {temp_c + 5:.0f}°C (1 hour at failure rate)"
                    }
                },
                {
                    "channel": "NOTIFICATION",
                    "action": "PAGE_ON_CALL",
                    "params": {
                        "escalation_level": "DIRECTOR",
                        "recipients": ["maintenance_director", "chief_pharmacist", "site_director"],
                        "urgency": "CRITICAL",
                        "message": f"CRITICAL ALERT: {data.get('equipment_id')} compressor failure. "
                                  f"Temperature rising at 0.8C/hr. Replacement required within 2 hours."
                    }
                },
                {
                    "channel": "COMPLIANCE",
                    "action": "INITIATE_DEVIATION_RESPONSE",
                    "params": {
                        "incident_type": "Equipment Failure - Critical",
                        "investigation_priority": "URGENT",
                        "product_assessment": "Required post-resolution"
                    }
                }
            ]
        })
        return decision
    
    # --- CRITICAL: Temperature > 8°C (product destruction) ---
    if temp_c > 8.0 and temp_c > -15.0:  # Rising trend detection
        decision.update({
            "analysis": f"CRITICAL: Temperature {temp_c:.1f}°C exceeds WHO product safety threshold (>8°C). "
                        "Vaccine and insulin potency severely compromised. Immediate product relocation required.",
            "severity": 1.0,
            "risk_level": "CRITICAL",
            "recoverable": False,
            "requires_human_approval": True,
            "approval_message": "APPROVAL REQUIRED: Authorize product destruction/quarantine and emergency refrigeration transfer",
            "action_plan": [
                {
                    "channel": "SAFETY",
                    "action": "EMERGENCY_PRODUCT_QUARANTINE",
                    "params": {
                        "affected_products": data.get("product_count", 0),
                        "product_type": data.get("product_type", "unknown"),
                        "discard_action": "MANDATORY",
                        "documentation": "WHO GxP Deviation Report, Product Destruction Certificate"
                    }
                },
                {
                    "channel": "COMPLIANCE",
                    "action": "FILE_DEVIATION_REPORT",
                    "params": {
                        "report_type": "Critical GxP Deviation",
                        "regulatory_body": "FDA/EMA",
                        "timeline": "Immediately",
                        "investigation_required": True
                    }
                },
                {
                    "channel": "NOTIFICATION",
                    "action": "PAGE_ON_CALL",
                    "params": {
                        "escalation_level": "C-SUITE",
                        "recipients": ["chief_pharmacist", "site_director", "quality_assurance"],
                        "urgency": "IMMEDIATE",
                        "message": f"CRITICAL ALERT: {data.get('equipment_id')} product excursion >8C. Products must be discarded."
                    }
                },
                {
                    "channel": "MAINTENANCE",
                    "action": "INVESTIGATE_ROOT_CAUSE",
                    "params": {
                        "compressor_status": compressor_ok,
                        "power_status": power_ok,
                        "seal_status": door_seal_ok,
                        "root_cause_analysis": "Full investigation required - escalate to engineering"
                    }
                }
            ]
        })
        return decision
    
    # --- CRITICAL: Power Failure (immediate backup activation) ---
    if not power_ok:
        decision.update({
            "analysis": "CRITICAL: Power failure detected. Backup cooling systems must activate immediately. "
                        "Without power, temperature will rise 2°C/hour to ambient.",
            "severity": 0.98,
            "risk_level": "CRITICAL",
            "recoverable": True,
            "requires_human_approval": True,
            "approval_message": "APPROVAL REQUIRED: Activate backup power/generator and monitor temperature recovery",
            "action_plan": [
                {
                    "channel": "MAINTENANCE",
                    "action": "ACTIVATE_BACKUP_POWER",
                    "params": {
                        "backup_type": "Generator/UPS",
                        "priority": "IMMEDIATE",
                        "monitoring_interval": "Every 5 minutes",
                        "estimated_time_to_critical": 11.0  # hours at 2C/hour rise
                    }
                },
                {
                    "channel": "SAFETY",
                    "action": "BEGIN_TEMPERATURE_MONITORING",
                    "params": {
                        "monitoring_start": "NOW",
                        "alert_threshold": 0.0,  # Any positive temp is warning
                        "escalation_trigger": "Temp > 5°C for > 10 minutes"
                    }
                },
                {
                    "channel": "NOTIFICATION",
                    "action": "PAGE_ON_CALL",
                    "params": {
                        "escalation_level": "DIRECTOR",
                        "recipients": ["facilities_director", "chief_pharmacist"],
                        "urgency": "IMMEDIATE",
                        "message": f"CRITICAL: {data.get('equipment_id')} power failure. Activating backup systems."
                    }
                },
                {
                    "channel": "MAINTENANCE",
                    "action": "RESTORE_MAIN_POWER",
                    "params": {
                        "priority": "HIGHEST",
                        "max_downtime_hours": 4.0,
                        "contingency": "Relocate products if main power not restored within 3 hours"
                    }
                }
            ]
        })
        return decision
    
    # --- CRITICAL: Sensor Drift > 3°C (actual temp hidden from display) ---
    if not temp_sensor_ok:
        temp_discrepancy = abs(actual_temp - temp_c)
        if temp_discrepancy > 3.0:
            decision.update({
                "analysis": f"CRITICAL: Sensor drift detected. Displayed temp {temp_c:.1f}°C but actual {actual_temp:.1f}°C "
                            f"({temp_discrepancy:.1f}°C discrepancy). All temperature readings unreliable. "
                            "Cannot trust equipment safety status.",
                "severity": 0.95,
                "risk_level": "CRITICAL",
                "recoverable": True,
                "requires_human_approval": True,
                "approval_message": "APPROVAL REQUIRED: Replace temperature sensor immediately, audit product integrity",
                "action_plan": [
                    {
                        "channel": "SAFETY",
                        "action": "QUARANTINE_EQUIPMENT",
                        "params": {
                            "status": "OUT_OF_SERVICE",
                            "reason": "Sensor malfunction - temperature not verified",
                            "auditable_record": True,
                            "product_inspection": "Visual inspection required"
                        }
                    },
                    {
                        "channel": "COMPLIANCE",
                        "action": "AUDIT_PRODUCT_INTEGRITY",
                        "params": {
                            "inspection_type": "Full physical inspection",
                            "documentation": "Ackermann testing for temperature-sensitive products",
                            "action_level": "Product sampling required"
                        }
                    },
                    {
                        "channel": "MAINTENANCE",
                        "action": "REPLACE_TEMPERATURE_SENSOR",
                        "params": {
                            "priority": "IMMEDIATE",
                            "max_downtime_hours": 2.0,
                            "verification": "Sensor calibration certificate required after replacement"
                        }
                    },
                    {
                        "channel": "NOTIFICATION",
                        "action": "PAGE_ON_CALL",
                        "params": {
                            "escalation_level": "MANAGER",
                            "recipients": ["biomedical_engineer", "chief_pharmacist"],
                            "urgency": "URGENT",
                            "message": f"Sensor malfunction on {data.get('equipment_id')}. Actual temp {actual_temp:.1f}C vs displayed {temp_c:.1f}C"
                        }
                    }
                ]
            })
            return decision
    
    # --- HIGH: Temperature > 5°C for extended period (compressor investigation) ---
    if temp_c > 5.0 and compressor_ok and power_ok:
        decision.update({
            "analysis": f"HIGH: Temperature {temp_c:.1f}°C above 5°C threshold. "
                        "Vaccine and insulin stability at risk. Compressor may be degrading. "
                        "Immediate investigation required.",
            "severity": 0.75,
            "risk_level": "HIGH",
            "recoverable": True,
            "requires_human_approval": True,
            "approval_message": "APPROVAL REQUIRED: Authorize compressor inspection and emergency product transfer if needed",
            "action_plan": [
                {
                    "channel": "MAINTENANCE",
                    "action": "INSPECT_COMPRESSOR",
                    "params": {
                        "priority": "URGENT",
                        "checks": ["coolant pressure", "motor amp draw", "discharge temp"],
                        "completion_target": "Within 2 hours"
                    }
                },
                {
                    "channel": "SAFETY",
                    "action": "BEGIN_PRODUCT_MONITORING",
                    "params": {
                        "inspection_interval": "Every 30 minutes",
                        "visual_inspection": True,
                        "trigger_transfer": "If temp > 5°C for > 2 hours"
                    }
                },
                {
                    "channel": "NOTIFICATION",
                    "action": "ALERT_PHARMACIST",
                    "params": {
                        "recipients": ["chief_pharmacist"],
                        "urgency": "HIGH",
                        "message": f"{data.get('equipment_id')} temp elevated. Compressor investigation underway."
                    }
                },
                {
                    "channel": "COMPLIANCE",
                    "action": "DOCUMENT_EXCURSION_INITIATION",
                    "params": {
                        "incident_type": "Temperature Excursion - Pending",
                        "trigger_time": "NOW",
                        "watchdog_threshold": "2 hours at >5°C"
                    }
                }
            ]
        })
        return decision
    
    # --- HIGH: Door seal breach + high humidity ---
    if not door_seal_ok and humidity_pct > 60.0:
        decision.update({
            "analysis": f"HIGH: Door seal breached with humidity {humidity_pct:.1f}% indicating warm air ingress. "
                        "Moisture can condense on products and equipment. Seal replacement required.",
            "severity": 0.70,
            "risk_level": "HIGH",
            "recoverable": True,
            "requires_human_approval": False,
            "approval_message": None,
            "action_plan": [
                {
                    "channel": "MAINTENANCE",
                    "action": "SCHEDULE_SEAL_REPLACEMENT",
                    "params": {
                        "priority": "URGENT",
                        "max_schedule_days": 2,
                        "interim_monitoring": "Temperature and humidity logged every 15 minutes"
                    }
                },
                {
                    "channel": "SAFETY",
                    "action": "INCREASE_MONITORING_FREQUENCY",
                    "params": {
                        "interval": "Every 15 minutes",
                        "check_points": ["temperature", "humidity", "ice_accumulation", "product_condensation"]
                    }
                },
                {
                    "channel": "NOTIFICATION",
                    "action": "NOTIFY_MAINTENANCE",
                    "params": {
                        "recipients": ["maintenance_supervisor"],
                        "urgency": "HIGH",
                        "message": f"Door seal breach on {data.get('equipment_id')} - schedule replacement"
                    }
                }
            ]
        })
        return decision
    
    # --- MEDIUM: Door seal breach (without high humidity) ---
    if not door_seal_ok:
        decision.update({
            "analysis": f"MEDIUM: Door seal compromised. Temperature {temp_c:.1f}°C and humidity {humidity_pct:.1f}% "
                        "currently acceptable but risk of deterioration.",
            "severity": 0.45,
            "risk_level": "MEDIUM",
            "recoverable": True,
            "requires_human_approval": False,
            "approval_message": None,
            "action_plan": [
                {
                    "channel": "MAINTENANCE",
                    "action": "SCHEDULE_SEAL_REPLACEMENT",
                    "params": {
                        "priority": "HIGH",
                        "max_schedule_days": 7,
                        "cost_impact": "Low - routine maintenance"
                    }
                },
                {
                    "channel": "SAFETY",
                    "action": "INCREASE_MONITORING_FREQUENCY",
                    "params": {
                        "interval": "Daily",
                        "check_points": ["humidity_trend", "temperature_stability"]
                    }
                }
            ]
        })
        return decision
    
    # --- LOW: Nominal operation ---
    decision.update({
        "analysis": f"NOMINAL: Equipment operating within WHO specifications. "
                    f"Temperature {temp_c:.1f}°C, humidity {humidity_pct:.1f}%, all systems functional.",
        "severity": 0.0,
        "risk_level": "LOW",
        "recoverable": True,
        "requires_human_approval": False,
        "approval_message": None,
        "action_plan": [
            {
                "channel": "MAINTENANCE",
                "action": "ROUTINE_MONITORING",
                "params": {
                    "interval": "Daily standard checks",
                    "escalation_trigger": "Any status change"
                }
            }
        ]
    })
    
    return decision


def decide_dispenser(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decision tree for DrugDispenser with access control and inventory management.
    
    Args:
        data: Snapshot dictionary from DrugDispenser.snapshot()
        
    Returns:
        Decision dictionary matching schema
    """
    decision_id = f"DEC-2026-DISPENSER-{data.get('equipment_id', 'UNKNOWN')}"
    
    temp_c = data.get("temp_c", 20.0)
    inventory_pct = data.get("inventory_pct", 50.0)
    motor_ok = data.get("motor_ok", True)
    unusual_access = data.get("unusual_access", False)
    access_count_24h = data.get("access_count_24h", 12)
    
    # Initialize decision
    decision = {
        "decision_id": decision_id,
        "analysis": "",
        "severity": 0.0,
        "risk_level": "LOW",
        "recoverable": True,
        "requires_human_approval": False,
        "approval_message": None,
        "action_plan": [],
    }
    
    # --- CRITICAL: Access anomaly (security risk) ---
    if unusual_access or access_count_24h > 50:
        decision.update({
            "analysis": f"CRITICAL: Access anomaly detected. Unusual access pattern suggests potential tampering or theft. "
                        f"{access_count_24h} access events in 24h (normal: 12-20). "
                        "Controlled substance security at risk.",
            "severity": 0.90,
            "risk_level": "CRITICAL",
            "recoverable": True,
            "requires_human_approval": True,
            "approval_message": "APPROVAL REQUIRED: Lock unit immediately, investigate access logs, notify DEA if applicable",
            "action_plan": [
                {
                    "channel": "SAFETY",
                    "action": "LOCK_UNIT_IMMEDIATELY",
                    "params": {
                        "dispense_capability": "DISABLED",
                        "physical_lock": "Engage",
                        "access_logs": "Preserved for forensic analysis"
                    }
                },
                {
                    "channel": "NOTIFICATION",
                    "action": "PAGE_SECURITY",
                    "params": {
                        "escalation_level": "DIRECTOR",
                        "recipients": ["security_director", "chief_pharmacist"],
                        "urgency": "IMMEDIATE",
                        "message": f"Security Alert: {data.get('equipment_id')} access anomaly detected. Unit locked."
                    }
                },
                {
                    "channel": "COMPLIANCE",
                    "action": "INITIATE_AUDIT",
                    "params": {
                        "audit_scope": "Access logs, dispensed quantities, expiration dates",
                        "dea_notification": True if "controlled" in data.get("drug_class", "").lower() else False,
                        "documentation": "DEA Form 106 (if applicable)"
                    }
                },
                {
                    "channel": "MAINTENANCE",
                    "action": "PRESERVE_EVIDENCE",
                    "params": {
                        "access_logs": "Export to secure storage",
                        "timestamp_range": "Last 7 days",
                        "device_status": "Do not reset"
                    }
                }
            ]
        })
        return decision
    
    # --- HIGH: Motor jam (mechanical failure) ---
    if not motor_ok:
        decision.update({
            "analysis": f"HIGH: Motor jam detected. Unit cannot dispense drugs. "
                        "Patients cannot receive medications from this dispenser. "
                        "Manual dispensing backup procedures required.",
            "severity": 0.85,
            "risk_level": "HIGH",
            "recoverable": True,
            "requires_human_approval": True,
            "approval_message": "APPROVAL REQUIRED: Activate manual dispensing procedures, route medication orders to alternate source",
            "action_plan": [
                {
                    "channel": "SAFETY",
                    "action": "DISABLE_DISPENSER",
                    "params": {
                        "status": "OUT_OF_SERVICE",
                        "reason": "Motor malfunction",
                        "manual_dispensing": "REQUIRED"
                    }
                },
                {
                    "channel": "NOTIFICATION",
                    "action": "ALERT_PHARMACY",
                    "params": {
                        "recipients": ["chief_pharmacist", "pharmacy_supervisor"],
                        "urgency": "HIGH",
                        "message": f"{data.get('equipment_id')} motor jam - route to manual dispensing",
                        "impact": "All medications routed to alternate dispensing station"
                    }
                },
                {
                    "channel": "MAINTENANCE",
                    "action": "REPAIR_MOTOR_ASSEMBLY",
                    "params": {
                        "priority": "URGENT",
                        "max_downtime_hours": 4.0,
                        "replacement_parts": "Motor assembly, control board diagnostics"
                    }
                },
                {
                    "channel": "COMPLIANCE",
                    "action": "DOCUMENT_DOWNTIME",
                    "params": {
                        "incident_type": "Equipment Failure - Motor",
                        "manual_dispensing_log": "REQUIRED",
                        "verification": "Pharmacist sign-off on all dispensing"
                    }
                }
            ]
        })
        return decision
    
    # --- HIGH: Temperature out of range (15-25°C) ---
    if temp_c < 15.0 or temp_c > 25.0:
        decision.update({
            "analysis": f"HIGH: Temperature {temp_c:.1f}°C outside safe range (15-25°C). "
                        "Temperature-sensitive drugs may be compromised. "
                        "All dispensed units since excursion must be flagged.",
            "severity": 0.80,
            "risk_level": "HIGH",
            "recoverable": True,
            "requires_human_approval": True,
            "approval_message": "APPROVAL REQUIRED: Flag all dispensed units for review, verify product integrity",
            "action_plan": [
                {
                    "channel": "SAFETY",
                    "action": "FLAG_DISPENSED_UNITS",
                    "params": {
                        "quarantine_since": "Last 4 hours",
                        "action": "Pharmacist review of dispensed quantities",
                        "patient_notification": "If critical medications affected"
                    }
                },
                {
                    "channel": "COMPLIANCE",
                    "action": "FILE_TEMPERATURE_DEVIATION",
                    "params": {
                        "deviation_type": "Environmental control failure",
                        "affected_products": "All temp-sensitive drugs",
                        "action_level": "Product review required"
                    }
                },
                {
                    "channel": "MAINTENANCE",
                    "action": "ENVIRONMENTAL_CONTROL_CHECK",
                    "params": {
                        "checks": ["HVAC function", "thermostat calibration", "room temperature"],
                        "priority": "URGENT"
                    }
                },
                {
                    "channel": "NOTIFICATION",
                    "action": "ALERT_PHARMACIST",
                    "params": {
                        "recipients": ["chief_pharmacist"],
                        "urgency": "HIGH",
                        "message": f"{data.get('equipment_id')} temp excursion to {temp_c:.1f}C - audit dispensed units"
                    }
                }
            ]
        })
        return decision
    
    # --- MEDIUM: Low inventory (< 10%) ---
    if inventory_pct < 10.0:
        decision.update({
            "analysis": f"MEDIUM: Inventory critically low at {inventory_pct:.1f}%. "
                        "Automatic reorder should trigger. Manual restock may be needed within hours.",
            "severity": 0.50,
            "risk_level": "MEDIUM",
            "recoverable": True,
            "requires_human_approval": False,
            "approval_message": None,
            "action_plan": [
                {
                    "channel": "COMPLIANCE",
                    "action": "TRIGGER_AUTO_REORDER",
                    "params": {
                        "priority": "URGENT",
                        "quantity": "Full refill",
                        "delivery_target": "Within 2 hours"
                    }
                },
                {
                    "channel": "NOTIFICATION",
                    "action": "NOTIFY_SUPPLY_CHAIN",
                    "params": {
                        "recipients": ["inventory_manager"],
                        "urgency": "HIGH",
                        "message": f"{data.get('equipment_id')} at {inventory_pct:.1f}% - expedite restock"
                    }
                }
            ]
        })
        return decision
    
    # --- MEDIUM: Inventory low (< 20%) ---
    if inventory_pct < 20.0:
        decision.update({
            "analysis": f"MEDIUM: Inventory low at {inventory_pct:.1f}%. "
                        "Schedule routine restock within business day.",
            "severity": 0.35,
            "risk_level": "MEDIUM",
            "recoverable": True,
            "requires_human_approval": False,
            "approval_message": None,
            "action_plan": [
                {
                    "channel": "COMPLIANCE",
                    "action": "SCHEDULE_RESTOCK",
                    "params": {
                        "priority": "HIGH",
                        "timeframe": "Within 8 hours",
                        "target_level": "85%+"
                    }
                },
                {
                    "channel": "NOTIFICATION",
                    "action": "NOTIFY_SUPPLY_CHAIN",
                    "params": {
                        "recipients": ["inventory_manager"],
                        "message": f"{data.get('equipment_id')} inventory at {inventory_pct:.1f}%"
                    }
                }
            ]
        })
        return decision
    
    # --- LOW: Nominal operation ---
    decision.update({
        "analysis": f"NOMINAL: Dispenser operating normally. "
                    f"Temperature {temp_c:.1f}°C, inventory {inventory_pct:.1f}%, no access anomalies.",
        "severity": 0.0,
        "risk_level": "LOW",
        "recoverable": True,
        "requires_human_approval": False,
        "approval_message": None,
        "action_plan": [
            {
                "channel": "MAINTENANCE",
                "action": "ROUTINE_MONITORING",
                "params": {
                    "interval": "Daily standard checks",
                    "access_log_review": "Weekly"
                }
            }
        ]
    })
    
    return decision


def decide_blood_storage(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decision tree for BloodStorage with critical contamination and temperature logic.
    
    Blood safety is paramount - temperature must stay 1-6°C (RBC at 4°C live 42 days).
    
    Args:
        data: Snapshot dictionary from BloodStorage.snapshot()
        
    Returns:
        Decision dictionary matching schema
    """
    decision_id = f"DEC-2026-BLOODSTORAGE-{data.get('equipment_id', 'UNKNOWN')}"
    
    temp_c = data.get("temp_c", 4.0)
    units_total = data.get("units_total", 200)
    units_expiring = data.get("units_expiring_48h", 0)
    contamination_risk = data.get("contamination_risk_pct", 2.0)
    co2_ppm = data.get("co2_ppm", 400.0)
    door_seal_ok = data.get("door_seal_ok", True)
    
    # Initialize decision
    decision = {
        "decision_id": decision_id,
        "analysis": "",
        "severity": 0.0,
        "risk_level": "LOW",
        "recoverable": True,
        "requires_human_approval": False,
        "approval_message": None,
        "action_plan": [],
    }
    
    # --- CRITICAL: Temperature freezing (< 1°C) - destroys RBCs ---
    if temp_c < 1.0:
        decision.update({
            "analysis": f"CRITICAL: Temperature {temp_c:.1f}°C below 1°C safety threshold. "
                        "Red blood cells freeze and rupture - all units damaged and non-transfusable. "
                        "ALL UNITS MUST BE DISCARDED.",
            "severity": 1.0,
            "risk_level": "CRITICAL",
            "recoverable": False,
            "requires_human_approval": True,
            "approval_message": "APPROVAL REQUIRED: Authorize destruction of all blood units, emergency supply activation",
            "action_plan": [
                {
                    "channel": "SAFETY",
                    "action": "EMERGENCY_UNIT_DESTRUCTION",
                    "params": {
                        "units_destroyed": units_total,
                        "action": "DISCARD_ALL",
                        "documentation": "Destruction certificate required",
                        "biohazard_handling": "Follow institutional protocol"
                    }
                },
                {
                    "channel": "COMPLIANCE",
                    "action": "FILE_CRITICAL_INCIDENT",
                    "params": {
                        "report_type": "Blood Product Loss",
                        "incident_level": "CRITICAL",
                        "fda_notification": True,
                        "aabb_notification": True
                    }
                },
                {
                    "channel": "NOTIFICATION",
                    "action": "PAGE_ON_CALL",
                    "params": {
                        "escalation_level": "C-SUITE",
                        "recipients": ["blood_bank_director", "medical_director", "hospital_administrator"],
                        "urgency": "IMMEDIATE",
                        "message": f"CRITICAL: {units_total} units destroyed due to freezing - activate emergency supply"
                    }
                },
                {
                    "channel": "MAINTENANCE",
                    "action": "URGENT_REPAIR",
                    "params": {
                        "priority": "HIGHEST",
                        "root_cause": "Thermostat malfunction or refrigerant leak",
                        "max_downtime": "Equipment replaced"
                    }
                }
            ]
        })
        return decision
    
    # --- CRITICAL: Temperature too warm (> 6°C) - bacterial growth ---
    if temp_c > 6.0:
        decision.update({
            "analysis": f"CRITICAL: Temperature {temp_c:.1f}°C exceeds 6°C safety threshold. "
                        "Bacterial contamination risk increases exponentially. "
                        f"{units_total} units at risk of bacterial sepsis transmission. Discard all units.",
            "severity": 1.0,
            "risk_level": "CRITICAL",
            "recoverable": False,
            "requires_human_approval": True,
            "approval_message": "APPROVAL REQUIRED: Authorize unit destruction, activate emergency blood supply protocols",
            "action_plan": [
                {
                    "channel": "SAFETY",
                    "action": "QUARANTINE_AND_DISCARD",
                    "params": {
                        "units_quarantined": units_total,
                        "reason": "Bacterial contamination risk",
                        "action": "DISCARD_ALL",
                        "culture_analysis": "Optional - retain for post-incident analysis only"
                    }
                },
                {
                    "channel": "COMPLIANCE",
                    "action": "FILE_CRITICAL_INCIDENT",
                    "params": {
                        "report_type": "Blood Contamination Risk",
                        "incident_level": "CRITICAL",
                        "aabb_notification": True,
                        "fda_notification": True,
                        "transfusion_medicine_review": True
                    }
                },
                {
                    "channel": "NOTIFICATION",
                    "action": "PAGE_ON_CALL",
                    "params": {
                        "escalation_level": "C-SUITE",
                        "recipients": ["blood_bank_director", "chief_medical_officer", "hospital_administrator"],
                        "urgency": "IMMEDIATE",
                        "message": f"CRITICAL: {units_total} blood units contaminated risk at {temp_c:.1f}C - activate emergency supply"
                    }
                },
                {
                    "channel": "MAINTENANCE",
                    "action": "IMMEDIATE_REPAIR",
                    "params": {
                        "priority": "HIGHEST",
                        "root_cause_investigation": "Thermostat failure or compressor malfunction",
                        "replacement": "Equipment replacement if unrecoverable"
                    }
                }
            ]
        })
        return decision
    
    # --- CRITICAL: Contamination risk > 30% or CO2 > 2000ppm ---
    if contamination_risk > 30.0 or co2_ppm > 2000.0:
        decision.update({
            "analysis": f"CRITICAL: Contamination risk {contamination_risk:.1f}% (threshold 30%) or CO2 {co2_ppm:.0f}ppm (threshold 2000). "
                        "Bacterial growth and gas accumulation indicate seal breach. Units must be cultured and quarantined.",
            "severity": 0.95,
            "risk_level": "CRITICAL",
            "recoverable": True,
            "requires_human_approval": True,
            "approval_message": "APPROVAL REQUIRED: Investigate seal breach, culture samples, quarantine units pending results",
            "action_plan": [
                {
                    "channel": "SAFETY",
                    "action": "QUARANTINE_UNITS",
                    "params": {
                        "units_affected": units_total,
                        "culture_analysis": True,
                        "hold_period": "Until culture results negative",
                        "transfusion_hold": "No release until cleared"
                    }
                },
                {
                    "channel": "COMPLIANCE",
                    "action": "INITIATE_CONTAMINATION_INVESTIGATION",
                    "params": {
                        "investigation_scope": "Seal integrity, storage conditions, previous units",
                        "sample_culture": "Mandatory",
                        "aabb_notification": True,
                        "incident_report": True
                    }
                },
                {
                    "channel": "MAINTENANCE",
                    "action": "INVESTIGATE_SEAL_BREACH",
                    "params": {
                        "seal_inspection": "Visual and pressure test",
                        "co2_source": "Investigate origin",
                        "priority": "URGENT"
                    }
                },
                {
                    "channel": "NOTIFICATION",
                    "action": "PAGE_BLOOD_BANK",
                    "params": {
                        "recipients": ["blood_bank_director", "transfusion_medicine"],
                        "urgency": "HIGH",
                        "message": f"Contamination risk {contamination_risk:.1f}% on {data.get('equipment_id')} - quarantine units"
                    }
                }
            ]
        })
        return decision
    
    # --- HIGH: CO2 high (1000-2000ppm) - contamination risk rising ---
    if co2_ppm > 1000.0:
        decision.update({
            "analysis": f"HIGH: CO2 level {co2_ppm:.0f}ppm indicates possible seal breach or microbial activity. "
                        "Contamination risk rising. Seal inspection needed.",
            "severity": 0.70,
            "risk_level": "HIGH",
            "recoverable": True,
            "requires_human_approval": False,
            "approval_message": None,
            "action_plan": [
                {
                    "channel": "MAINTENANCE",
                    "action": "INVESTIGATE_SEAL_INTEGRITY",
                    "params": {
                        "inspection": "Visual check for gaps or damage",
                        "priority": "URGENT",
                        "schedule": "Within 24 hours"
                    }
                },
                {
                    "channel": "SAFETY",
                    "action": "INCREASE_MONITORING",
                    "params": {
                        "interval": "Every 4 hours",
                        "parameters": ["CO2 level", "temperature", "contamination risk"],
                        "alert_threshold": "CO2 > 1500 ppm"
                    }
                },
                {
                    "channel": "COMPLIANCE",
                    "action": "DOCUMENT_OBSERVATION",
                    "params": {
                        "observation_type": "Elevated CO2 - monitoring status",
                        "escalation_trigger": "If CO2 continues rising"
                    }
                }
            ]
        })
        return decision
    
    # --- MEDIUM: Units expiring 48 hours (> 5 units) ---
    if units_expiring > 5:
        decision.update({
            "analysis": f"MEDIUM: {units_expiring} units expiring within 48 hours (42-day shelf life). "
                        "Coordinate with blood bank for transfusion or destruction.",
            "severity": 0.40,
            "risk_level": "MEDIUM",
            "recoverable": True,
            "requires_human_approval": False,
            "approval_message": None,
            "action_plan": [
                {
                    "channel": "COMPLIANCE",
                    "action": "ALERT_BLOOD_BANK_COORDINATOR",
                    "params": {
                        "units_expiring": units_expiring,
                        "action": "Prioritize for transfusion or discard",
                        "deadline": "48 hours"
                    }
                },
                {
                    "channel": "NOTIFICATION",
                    "action": "NOTIFY_BLOOD_BANK",
                    "params": {
                        "recipients": ["blood_bank_coordinator"],
                        "urgency": "MEDIUM",
                        "message": f"{units_expiring} units expiring on {data.get('equipment_id')} within 48 hours"
                    }
                }
            ]
        })
        return decision
    
    # --- LOW: Nominal operation ---
    decision.update({
        "analysis": f"NOMINAL: Blood storage operating within specifications. "
                    f"Temperature {temp_c:.1f}°C (safe: 1-6°C), {units_total} units stored, "
                    f"contamination risk {contamination_risk:.1f}%, CO2 {co2_ppm:.0f}ppm.",
        "severity": 0.0,
        "risk_level": "LOW",
        "recoverable": True,
        "requires_human_approval": False,
        "approval_message": None,
        "action_plan": [
            {
                "channel": "MAINTENANCE",
                "action": "ROUTINE_MONITORING",
                "params": {
                    "interval": "Daily temperature and unit count verification",
                    "escalation_trigger": "Any parameter change"
                }
            }
        ]
    })
    
    return decision


def decide_fleet(site_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fleet-level decision tree for multi-site pharmaceutical equipment management.
    
    Detects cascading failures, site-wide power loss, and coordinates emergency
    product transfers between sites.
    
    Args:
        site_metrics: Aggregated metrics across all sites and equipment
        Expects: {
            "sites": {"site_a": {"critical_count": int, "equipment": [...]}, ...},
            "total_equipment": int,
            "total_critical": int,
            "total_units_at_risk": int,
        }
        
    Returns:
        Decision dictionary matching schema
    """
    decision_id = "DEC-2026-FLEET-COORDINATION"
    
    sites = site_metrics.get("sites", {})
    total_equipment = site_metrics.get("total_equipment", 0)
    total_critical = site_metrics.get("total_critical", 0)
    total_units_at_risk = site_metrics.get("total_units_at_risk", 0)
    
    # Initialize decision
    decision = {
        "decision_id": decision_id,
        "analysis": "",
        "severity": 0.0,
        "risk_level": "LOW",
        "recoverable": True,
        "requires_human_approval": False,
        "approval_message": None,
        "action_plan": [],
    }
    
    # Count failures by type
    power_failures = sum(
        1 for site_data in sites.values()
        for eq in site_data.get("equipment", [])
        if eq.get("status") == "POWER_LOSS"
    )
    
    critical_count = sum(
        1 for site_data in sites.values()
        if site_data.get("critical_count", 0) > 0
    )
    
    # --- CRITICAL: Multi-site power failure (> 1 site affected) ---
    if power_failures > 1 and critical_count > 1:
        affected_sites = [
            site_name for site_name, site_data in sites.items()
            if any(eq.get("status") == "POWER_LOSS" for eq in site_data.get("equipment", []))
        ]
        
        decision.update({
            "analysis": f"CRITICAL: Multi-site power failure detected. {len(affected_sites)} sites affected: {', '.join(affected_sites)}. "
                        f"{total_units_at_risk} units at risk. Cascading failure may overwhelm regional capacity.",
            "severity": 0.98,
            "risk_level": "CRITICAL",
            "recoverable": True,
            "requires_human_approval": True,
            "approval_message": "APPROVAL REQUIRED: Activate disaster recovery protocol, coordinate emergency product transfers",
            "action_plan": [
                {
                    "channel": "SAFETY",
                    "action": "ACTIVATE_DISASTER_RECOVERY",
                    "params": {
                        "sites_affected": affected_sites,
                        "backup_activation": "ALL_SITES",
                        "coordination_center": "Regional logistics hub",
                        "emergency_status": "DECLARED"
                    }
                },
                {
                    "channel": "NOTIFICATION",
                    "action": "ESCALATE_EXECUTIVE",
                    "params": {
                        "escalation_level": "BOARD",
                        "recipients": ["regional_director", "hospital_ceos"],
                        "urgency": "IMMEDIATE",
                        "message": f"CRITICAL: Multi-site power failure. {total_units_at_risk} units at risk."
                    }
                },
                {
                    "channel": "COMPLIANCE",
                    "action": "ACTIVATE_EMERGENCY_PROTOCOLS",
                    "params": {
                        "protocol": "Disaster Recovery Plan",
                        "coordination": "State health department notification",
                        "backup_supplier": "Activate emergency blood supplier"
                    }
                },
                {
                    "channel": "MAINTENANCE",
                    "action": "COORDINATE_EQUIPMENT_TRANSFER",
                    "params": {
                        "source_sites": affected_sites,
                        "destination": "Functional backup facilities",
                        "coordination": "Regional equipment pool"
                    }
                }
            ]
        })
        return decision
    
    # --- HIGH: Single site power failure ---
    if power_failures == 1:
        affected_site = next(
            (site_name for site_name, site_data in sites.items()
             if any(eq.get("status") == "POWER_LOSS" for eq in site_data.get("equipment", []))),
            "UNKNOWN"
        )
        
        decision.update({
            "analysis": f"HIGH: Power failure at {affected_site}. All refrigeration equipment at risk. "
                        f"Backup power activation and emergency product relocation required.",
            "severity": 0.85,
            "risk_level": "HIGH",
            "recoverable": True,
            "requires_human_approval": True,
            "approval_message": "APPROVAL REQUIRED: Authorize inter-site product transfer, activate backup power",
            "action_plan": [
                {
                    "channel": "MAINTENANCE",
                    "action": "ACTIVATE_SITE_BACKUP_POWER",
                    "params": {
                        "site": affected_site,
                        "backup_type": "Generator",
                        "priority": "IMMEDIATE"
                    }
                },
                {
                    "channel": "SAFETY",
                    "action": "INITIATE_PRODUCT_TRANSFER",
                    "params": {
                        "source_site": affected_site,
                        "destination": "Nearest operational facility",
                        "units_to_transfer": total_units_at_risk,
                        "coordination": "Regional logistics"
                    }
                },
                {
                    "channel": "COMPLIANCE",
                    "action": "DOCUMENT_INCIDENT",
                    "params": {
                        "incident_type": "Multi-site Coordination - Power Loss",
                        "transfer_logs": "Temperature-monitored transport"
                    }
                },
                {
                    "channel": "NOTIFICATION",
                    "action": "NOTIFY_REGIONAL_DIRECTOR",
                    "params": {
                        "recipients": ["regional_director", "site_director"],
                        "urgency": "HIGH",
                        "message": f"Power failure at {affected_site} - transferring {total_units_at_risk} units"
                    }
                }
            ]
        })
        return decision
    
    # --- HIGH: Many critical failures (> 30% of fleet) ---
    if total_critical >= total_equipment * 0.30 and total_critical > 0:
        decision.update({
            "analysis": f"HIGH: {total_critical}/{total_equipment} equipment in critical state ({total_critical/total_equipment*100:.0f}%). "
                        "Fleet-wide reliability compromised. Urgent maintenance intervention required.",
            "severity": 0.75,
            "risk_level": "HIGH",
            "recoverable": True,
            "requires_human_approval": False,
            "approval_message": None,
            "action_plan": [
                {
                    "channel": "MAINTENANCE",
                    "action": "ESCALATE_MAINTENANCE_PRIORITY",
                    "params": {
                        "critical_equipment_count": total_critical,
                        "fleet_percentage": f"{total_critical/total_equipment*100:.0f}%",
                        "action": "Divert resources to highest-criticality repairs"
                    }
                },
                {
                    "channel": "COMPLIANCE",
                    "action": "ESCALATE_FLEET_STATUS",
                    "params": {
                        "status": "DEGRADED",
                        "reliability_metric": f"{(total_equipment - total_critical)/total_equipment*100:.0f}%"
                    }
                },
                {
                    "channel": "NOTIFICATION",
                    "action": "NOTIFY_OPERATIONS",
                    "params": {
                        "recipients": ["operations_director", "maintenance_manager"],
                        "urgency": "HIGH",
                        "message": f"Fleet status DEGRADED: {total_critical} units critical"
                    }
                }
            ]
        })
        return decision
    
    # --- MEDIUM: Some critical equipment (< 30%) ---
    if total_critical > 0:
        decision.update({
            "analysis": f"MEDIUM: {total_critical} equipment in critical state. Localized issues detected. "
                        "Monitor for escalation to fleet-wide impact.",
            "severity": 0.50,
            "risk_level": "MEDIUM",
            "recoverable": True,
            "requires_human_approval": False,
            "approval_message": None,
            "action_plan": [
                {
                    "channel": "MAINTENANCE",
                    "action": "PRIORITIZE_MAINTENANCE",
                    "params": {
                        "critical_count": total_critical,
                        "schedule": "Within 24 hours"
                    }
                },
                {
                    "channel": "COMPLIANCE",
                    "action": "MONITOR_FLEET_STATUS",
                    "params": {
                        "monitoring_interval": "Every 4 hours",
                        "escalation_trigger": "Any new critical alerts"
                    }
                }
            ]
        })
        return decision
    
    # --- LOW: Fleet nominal ---
    decision.update({
        "analysis": f"NOMINAL: Fleet healthy. {total_equipment} units operational, no critical alerts. "
                    "All sites within specification.",
        "severity": 0.0,
        "risk_level": "LOW",
        "recoverable": True,
        "requires_human_approval": False,
        "approval_message": None,
        "action_plan": [
            {
                "channel": "MAINTENANCE",
                "action": "ROUTINE_FLEET_MONITORING",
                "params": {
                    "interval": "Daily status check",
                    "sites": list(sites.keys()),
                    "escalation_trigger": "Any equipment status change"
                }
            }
        ]
    })
    
    return decision


def triage(appliance_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatcher function that routes equipment data to the appropriate decision tree.
    
    Single entry point for all decision-making logic. Routes based on equipment_type
    field in the snapshot data.
    
    Args:
        appliance_data: Snapshot dictionary from any equipment type
        
    Returns:
        Decision dictionary from the appropriate decision tree
    """
    eq_type = appliance_data.get("equipment_type", "UNKNOWN")
    
    if eq_type == "PharmaFreezer":
        return decide_freezer(appliance_data)
    elif eq_type == "DrugDispenser":
        return decide_dispenser(appliance_data)
    elif eq_type == "BloodStorage":
        return decide_blood_storage(appliance_data)
    else:
        # Fallback for unknown type
        return {
            "decision_id": f"DEC-2026-UNKNOWN-{appliance_data.get('equipment_id', 'UNKNOWN')}",
            "analysis": f"Unknown equipment type: {eq_type}",
            "severity": 0.5,
            "risk_level": "MEDIUM",
            "recoverable": True,
            "requires_human_approval": True,
            "approval_message": "Equipment type not recognized - manual review required",
            "action_plan": [
                {
                    "channel": "COMPLIANCE",
                    "action": "MANUAL_REVIEW",
                    "params": {
                        "reason": "Unknown equipment type",
                        "equipment_id": appliance_data.get("equipment_id")
                    }
                }
            ]
        }


if __name__ == "__main__":
    # Example usage
    print("=" * 80)
    print("PharmaSense AI — Pharmaceutical Equipment Simulation Engine")
    print("=" * 80)
    
    # Create mock database
    db = mock_db()
    
    # Run simulation for 10 hours
    dt_hours = 0.5
    num_steps = 20
    
    print(f"\nSimulating {num_steps} steps of {dt_hours} hours each...\n")
    
    # Simulate all equipment
    for category, equipment_list in db.items():
        print(f"\n{category.upper().replace('_', ' ')}")
        print("-" * 80)
        
        for equipment in equipment_list:
            # Run simulation
            for _ in range(num_steps):
                equipment.step(dt_hours)
            
            # Get snapshot
            snapshot = equipment.snapshot(datetime.now())
            prediction = predict_failure(snapshot)
            
            # Display results
            print(f"\n{equipment.equipment_id} ({equipment.profile})")
            print(f"  Status: {snapshot['status']}")
            print(f"  Temp: {snapshot['temp_c']}°C")
            
            if prediction["predicted_failure"] != "NONE":
                print(f"  [WARN] Predicted Failure: {prediction['predicted_failure']}")
                print(f"     Confidence: {prediction['confidence']:.1%}")
                print(f"     Root Cause: {prediction['root_cause']}")
                print(f"     Time to Critical: {prediction['time_to_critical_hours']:.1f} hours")
