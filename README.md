# PharmaSense AI — Pharmaceutical Equipment Simulation Engine

A complete Python physics simulation system for three types of pharmaceutical equipment with realistic failure modes, predictive analytics, and telemetry capture.

## Overview

PharmaSense AI simulates pharmaceutical equipment operations with:
- **Realistic physics** for temperature dynamics, humidity accumulation, and contamination
- **Multiple failure profiles** for each equipment type
- **Predictive failure detection** with confidence scores and time-to-critical estimates
- **State machine-based status reporting** with multi-level fault conditions
- **Snapshot telemetry** for integration with monitoring systems

## Equipment Types

### 1. PharmaFreezer (Class: `PharmaFreezer`)

Ultra-low temperature storage for vaccines, insulin, and blood plasma at -20°C to -80°C.

**Profiles:**
- `nominal` - Normal operation
- `compressor_failure` - Cooling system failure (0.8°C/hour warming)
- `door_seal_breach` - Compromised door seal (warm air ingress, humidity spike)
- `power_failure` - Lost electrical power (2°C/hour warming, accelerated)
- `sensor_drift` - Temperature sensor malfunction (actual temp hidden from display)

**State Variables:**
- `temp_c` - Display temperature
- `actual_temp_c` - True temperature (reveals sensor drift)
- `humidity_pct` - Internal humidity
- `compressor_ok`, `power_ok`, `door_seal_ok`, `temp_sensor_ok` - Component status
- `vibration_g`, `coolant_pressure_bar` - Operating parameters
- `product_count`, `product_type` - Inventory info

**Status Labels:**
- `NOMINAL` - Operating within specification
- `TEMP_WARNING` - Temp > -18°C
- `TEMP_CRITICAL` - Temp > -16°C
- `TEMP_EXCURSION` - Temp > -12°C (product damage risk)
- `SENSOR_FAULT` - Sensor drift detected
- `POWER_LOSS` - Power disconnected
- `COMPRESSOR_FAIL` - Compressor inoperable
- `DOOR_BREACH` - Seal compromised

**Physics:**
```
Temperature dynamics:
- Compressor failure: +0.8°C/hour (linear rise toward ambient)
- Power failure: +2.0°C/hour (faster rise)
- Door breach: +0.3°C/hour + humidity rise at 2%/hour
- Sensor drift: Actual temp rises +0.5°C/hour while display stays fixed

Operational vibration (sinusoidal):
- Normal: 0.1 ± 0.05g at 2Hz
- Failed: 0.05g baseline
```

### 2. DrugDispenser (Class: `DrugDispenser`)

Automated pharmaceutical distribution system maintaining 15-25°C.

**Profiles:**
- `nominal` - Normal operation
- `inventory_low` - 15% stock level
- `access_anomaly` - Suspicious access pattern (potential theft/tampering)
- `motor_jam` - Mechanical failure preventing dispensing
- `temp_out_of_range` - Environmental control failure

**State Variables:**
- `temp_c`, `humidity_pct` - Environmental conditions
- `inventory_pct` - Current drug stock (0-100%)
- `motor_ok` - Mechanical system status
- `access_count_24h` - Access attempts in 24-hour window
- `unusual_access` - Boolean flag for anomaly
- `dispense_accuracy_pct` - Accuracy of dosage delivery
- `last_access_user` - Last user to access system

**Status Labels:**
- `NOMINAL` - All systems normal
- `INVENTORY_LOW` - Stock < 20%
- `ACCESS_ANOMALY` - Suspicious access patterns detected
- `MOTOR_JAM` - Mechanical failure
- `TEMP_ALERT` - Outside 15-25°C safe range

**Physics:**
```
Inventory dynamics:
- Normal depletion: -0.5%/hour during operation
- Motor jam: No depletion (stuck)

Temperature control:
- PI controller behavior
- Heating/cooling rates: ±0.3-0.5°C/hour toward setpoint

Access anomaly:
- Grows at +2 events/hour when active
```

### 3. BloodStorage (Class: `BloodStorage`)

Blood bank refrigerator maintaining 1-6°C for 42-day shelf-life units.

**Profiles:**
- `nominal` - Normal operation
- `temp_excursion` - Temperature deviation (8.5°C initial)
- `unit_expiry` - Many units near 42-day expiry
- `contamination_risk` - High CO2 or pathogen risk
- `seal_breach` - Door seal failure

**State Variables:**
- `temp_c` - Storage temperature
- `units_total` - Total units stored
- `units_expiring_48h` - Units approaching shelf-life end
- `contamination_risk_pct` - Contamination probability (0-100%)
- `door_seal_ok` - Physical seal status
- `co2_ppm` - CO2 concentration (contamination indicator)
- `agitation_g` - Vibration/movement monitoring

**Status Labels:**
- `NOMINAL` - All parameters normal
- `TEMP_EXCURSION` - Outside 1-6°C range
- `EXPIRY_ALERT` - Many units near 42-day limit
- `CONTAMINATION_RISK` - High contamination risk (>20%) or CO2 > 2000ppm

**Physics:**
```
Temperature dynamics:
- Regulation: ±0.3-0.4°C/hour PI control
- Seal breach adds: +0.2°C/hour

Contamination growth:
- Base: 2% risk
- High CO2 adds: +0.1 * (CO2/1000 - 1)%/hour
- Seal breach adds: +20 ppm/hour CO2 rise

Unit expiry:
- Linear progression: units_expiring_48h grows over storage period
- 42-day shelf life tracked from creation time
```

## Usage

### Basic Simulation

```python
from pharma_sense_ai import PharmaFreezer, mock_db, predict_failure
from datetime import datetime

# Create equipment
freezer = PharmaFreezer("FZ-01", profile="nominal")

# Advance simulation by 5 hours in 0.5-hour steps
for _ in range(10):
    freezer.step(0.5)

# Get equipment state snapshot
snapshot = freezer.snapshot(datetime.now())
print(f"Temperature: {snapshot['temp_c']}°C")
print(f"Status: {snapshot['status']}")

# Get failure prediction
prediction = predict_failure(snapshot)
print(f"Predicted Failure: {prediction['predicted_failure']}")
print(f"Confidence: {prediction['confidence']:.0%}")
print(f"Time to Critical: {prediction['time_to_critical_hours']:.1f} hours")
```

### Mock Database

```python
# Create complete test environment with 11 equipment units
db = mock_db()

# Iterate through all equipment
for category, equipment_list in db.items():
    for equipment in equipment_list:
        equipment.step(2.0)  # Simulate 2 hours
        snapshot = equipment.snapshot(datetime.now())
        print(f"{snapshot['equipment_id']}: {snapshot['status']}")
```

## Failure Prediction Algorithm

The `predict_failure()` function analyzes equipment telemetry and returns:

```python
{
    "predicted_failure": str,           # Failure type or "NONE"
    "confidence": float,                # 0.0-1.0 confidence score
    "root_cause": str,                  # Description of underlying cause
    "time_to_critical_hours": float     # Hours until critical condition
}
```

### Detection Examples

**PharmaFreezer:**
- Compressor failure: Detected via `compressor_ok=False` or low pressure, confidence 95%, 0.8°C/hour rise
- Power loss: Detected via `power_ok=False`, confidence 98%, 2.0°C/hour rise
- Sensor drift: Detected via `temp_sensor_ok=False` with rising actual_temp_c, confidence 80%

**DrugDispenser:**
- Motor jam: Detected via `motor_ok=False`, confidence 92%, immediate critical state
- Access anomaly: Detected via `unusual_access=True` or `access_count_24h>40`, confidence 88%
- Inventory depletion: Tracked and predicted based on current level

**BloodStorage:**
- Temperature excursion: Detected when temp < 1°C or > 6°C, confidence 96%
- Unit expiry: Predicted from `units_expiring_48h > 50`, confidence 95%
- Contamination: Detected via `contamination_risk_pct > 30%` or `co2_ppm > 3000`, confidence 93%

## Snapshot Format

All equipment return flat dictionaries via `snapshot(timestamp)`:

```python
{
    "equipment_id": "FZ-01",
    "equipment_type": "PharmaFreezer",
    "profile": "compressor_failure",
    "product_type": "vaccine_storage",
    "site_name": "site_a",
    "timestamp": "2026-06-15T10:30:00",
    "status": "COMPRESSOR_FAIL",
    "temp_c": 3.5,
    "humidity_pct": 45.2,
    # ... additional fields per equipment type
}
```

## Mock Database

The `mock_db()` function creates a test environment with 11 equipment units:

**PharmaFreezer (5 units):**
- FZ-01: compressor_failure, vaccine_storage, site_a
- FZ-02: door_seal_breach, insulin_storage, site_a
- FZ-03: nominal, blood_plasma, site_b
- FZ-04: power_failure, vaccine_storage, site_b
- FZ-05: sensor_drift, general_meds, site_c

**DrugDispenser (3 units):**
- DD-01: access_anomaly, controlled_substances, site_a
- DD-02: inventory_low, general_meds, site_b
- DD-03: motor_jam, oncology_meds, site_c

**BloodStorage (3 units):**
- BS-01: temp_excursion, blood_bank, site_a
- BS-02: unit_expiry, blood_bank, site_b
- BS-03: nominal, blood_bank, site_c

## Physics Model

All physics uses deterministic, correlated calculations (no randomness):

### Temperature Excursions
- **Approach:** Linear addition of rates per `dt_hours`
- **Realism:** Different failure modes produce different warming curves
- **Example:** Compressor failure adds +0.8°C/hour; power loss adds +2.0°C/hour

### Humidity Dynamics
- **Door seal breach:** +2.0% per hour until saturation (95%)
- **Normal operation:** Stable at nominal levels

### Inventory Tracking
- **Normal use:** -0.5% per hour (depletes over ~200 hours)
- **Motor jam:** Stagnant inventory
- **Accuracy degradation:** -1% per hour when motor jammed

### Environmental Control
- **PI Controller behavior:** Proportional integral error correction
- **Recovery rate:** Equipment recovers toward setpoint at 0.3-0.4°C/hour

## Files

- **pharma_sense_ai.py** - Main simulation engine (Apache 2.0 licensed)
- **test_pharma_sense.py** - Comprehensive test suite with 6 test categories

## Testing

Run the comprehensive test suite:

```bash
python test_pharma_sense.py
```

Tests validate:
1. Physics calculations (temperature rise rates, humidity dynamics)
2. State machine transitions (status labels)
3. Snapshot format and completeness
4. Failure prediction accuracy
5. All equipment types

## License

Licensed under the Apache License, Version 2.0. See license header in source files.

## Example Output

```
FZ-01 (compressor_failure)
  Status: COMPRESSOR_FAIL
  Temp: -12.0C
  Predicted Failure: COMPRESSOR_FAILURE
     Confidence: 95.0%
     Root Cause: Compressor not operational or low coolant pressure
     Time to Critical: 42.5 hours

FZ-05 (sensor_drift)
  Status: TEMP_CRITICAL
  Temp: -20.0C (displayed)
  Actual Temp: -14.0C (actual - hidden!)
  Predicted Failure: SENSOR_DRIFT
     Confidence: 80.0%
     Root Cause: Temperature sensor reading error, actual temp drifting
     Time to Critical: 12.0 hours
```

## Integration Tips

### With Splunk
Export snapshots to JSON and forward to Splunk:
```python
import json
snapshot = equipment.snapshot(datetime.now())
print(json.dumps(snapshot))
```

### With Time Series Databases
Stream snapshots to InfluxDB, Prometheus, or similar:
```python
for equipment in db["pharma_freezers"]:
    equipment.step(1.0)
    snapshot = equipment.snapshot(datetime.now())
    # Write to time-series database
```

### With Alert Systems
Trigger alerts on predicted failures:
```python
prediction = predict_failure(snapshot)
if prediction["confidence"] > 0.85:
    send_alert(prediction)
```
