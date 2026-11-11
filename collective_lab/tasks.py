from __future__ import annotations

from .core import EvidenceItem, FaultTask


CANDIDATES = (
    "pump_cavitation",
    "heat_exchanger_fouling",
    "temperature_sensor_bias",
    "bypass_valve_stuck_open",
    "transient_load_no_fault",
)


def _items(rows: list[tuple[str, str, int, str, str]]) -> tuple[EvidenceItem, ...]:
    return tuple(EvidenceItem(*row) for row in rows)


def engineering_tasks() -> tuple[FaultTask, ...]:
    return (_additive(), _relational(), _coordination_trap())


def _briefing(site: str) -> str:
    return (
        f"The fictional {site} thermal-control loop is removing less heat than expected. "
        "Exactly one listed diagnosis is correct. Purchase evidence from the catalogue, "
        "integrate the results, and return calibrated probabilities."
    )


def _additive() -> FaultTask:
    rows = [
        ("A01", "hydraulics", 1, "Check pump inlet pressure snapshot", "Pump inlet pressure is stable and above the cavitation margin."),
        ("A02", "hydraulics", 3, "Inspect pump vibration spectrum", "No cavitation-frequency vibration is present."),
        ("A03", "thermal", 1, "Read exchanger inlet temperature", "Inlet temperature is within the normal operating band."),
        ("A04", "thermal", 3, "Measure exchanger temperature approach", "The hot-side approach is 8.4 C above its clean baseline."),
        ("A05", "thermal", 8, "Run controlled exchanger performance test", "Heat-transfer coefficient is 39% below the clean reference at matched flow."),
        ("A06", "flow", 1, "Read main-loop flow meter", "Main-loop flow is 98% of commanded flow."),
        ("A07", "flow", 3, "Cross-check flow with portable meter", "Portable meter agrees with the installed meter within 2%."),
        ("A08", "controls", 1, "Read bypass-valve command", "Bypass command is fully closed."),
        ("A09", "controls", 3, "Verify bypass-valve position", "Independent position indicator confirms the bypass is closed."),
        ("A10", "sensors", 1, "Compare temperature sensors", "Primary and reference temperature sensors agree within calibration tolerance."),
        ("A11", "maintenance", 3, "Inspect maintenance history", "Exchanger cleaning is 14 months overdue."),
        ("A12", "maintenance", 8, "Borescope exchanger channels", "Widespread mineral deposition narrows multiple exchanger channels."),
        ("A13", "operations", 1, "Check current process load", "Process load is steady and 4% below design maximum."),
        ("A14", "operations", 3, "Review the last six hours", "The cooling deficit persisted under three different stable loads."),
        ("A15", "electrical", 1, "Read pump motor current", "Motor current is normal for the measured flow."),
        ("A16", "electrical", 3, "Inspect motor phase balance", "Phase currents are balanced."),
        ("A17", "ambient", 1, "Read ambient temperature", "Ambient temperature is normal for the site."),
        ("A18", "ambient", 3, "Check intake obstruction", "The external intake path is clear."),
        ("A19", "records", 8, "Compare with commissioning data", "The same flow now produces materially less heat transfer than at commissioning."),
        ("A20", "records", 1, "Read operator note", "An operator reports a faint hum near the pump; no measurement corroborates it."),
    ]
    return FaultTask("eng-additive-001", "additive", "moderate", _briefing("Orion greenhouse"), CANDIDATES, "heat_exchanger_fouling", _items(rows))


def _relational() -> FaultTask:
    rows = [
        ("R01", "sensors", 1, "Read primary outlet sensor", "Primary outlet sensor reports 74.2 C."),
        ("R02", "sensors", 3, "Read independent reference sensor", "Reference sensor reports 61.0 C at the same point."),
        ("R03", "sensors", 8, "Bench-calibrate primary sensor", "Primary sensor has a stable +13.1 C offset across its working range."),
        ("R04", "controls", 1, "Read controller cooling demand", "Controller demand is near maximum because it trusts the primary sensor."),
        ("R05", "controls", 3, "Recompute demand from reference sensor", "Reference-based demand would be normal rather than maximum."),
        ("R06", "thermal", 1, "Read exchanger approach using primary sensor", "Primary-derived approach appears abnormally high."),
        ("R07", "thermal", 3, "Recompute exchanger approach using reference sensor", "Reference-derived approach is within the clean baseline."),
        ("R08", "hydraulics", 1, "Check pump inlet pressure", "Pressure is safely above the cavitation margin."),
        ("R09", "hydraulics", 3, "Inspect pump vibration", "Vibration is normal with no cavitation signature."),
        ("R10", "flow", 1, "Read installed flow meter", "Installed meter reports normal flow."),
        ("R11", "flow", 3, "Cross-check flow independently", "Independent flow estimate agrees within 3%."),
        ("R12", "controls", 1, "Read bypass command", "Bypass command is closed."),
        ("R13", "controls", 8, "Trace bypass flow", "Tracer confirms negligible bypass flow."),
        ("R14", "maintenance", 1, "Check exchanger service date", "The exchanger was cleaned recently."),
        ("R15", "maintenance", 8, "Run exchanger performance test", "Heat transfer matches the clean reference when reference temperatures are used."),
        ("R16", "operations", 1, "Read process load", "Load is steady and ordinary."),
        ("R17", "operations", 3, "Review alarm sequence", "The apparent cooling loss began immediately after primary-sensor replacement."),
        ("R18", "electrical", 1, "Read pump motor current", "Current is normal."),
        ("R19", "ambient", 3, "Check ambient correction", "Ambient correction cannot explain the 13 C sensor disagreement."),
        ("R20", "records", 1, "Read technician note", "A technician suspected exchanger fouling before comparing the sensors."),
    ]
    return FaultTask("eng-relational-001", "relational", "moderate", _briefing("Lyra archive"), CANDIDATES, "temperature_sensor_bias", _items(rows))


def _coordination_trap() -> FaultTask:
    rows = [
        ("T01", "hydraulics", 1, "Read pump inlet pressure", "A brief low-pressure sample lies close to the cavitation warning threshold."),
        ("T02", "hydraulics", 1, "Listen for pump noise", "An operator describes intermittent gravel-like noise."),
        ("T03", "hydraulics", 3, "Capture long vibration spectrum", "The apparent cavitation feature disappears when valve transitions are excluded."),
        ("T04", "hydraulics", 8, "Run controlled suction-margin test", "Pump performance remains normal throughout the verified suction-margin range."),
        ("T05", "flow", 1, "Read main-loop flow", "Main-loop flow is lower than command."),
        ("T06", "flow", 3, "Measure branch flows", "Unexpected flow is present in the bypass branch."),
        ("T07", "flow", 8, "Inject tracer upstream of bypass", "Tracer shows 31% of coolant bypasses the exchanger despite a closed command."),
        ("T08", "controls", 1, "Read bypass command", "Controller commands the bypass fully closed."),
        ("T09", "controls", 3, "Read actuator electrical feedback", "Actuator electronics report closed."),
        ("T10", "controls", 8, "Inspect mechanical valve position", "The valve stem is mechanically jammed at 29% open; electrical feedback is false."),
        ("T11", "thermal", 1, "Read exchanger inlet temperature", "Inlet temperature is normal."),
        ("T12", "thermal", 3, "Measure exchanger-only temperature change", "Temperature change across the exchanger is normal for the flow that actually enters it."),
        ("T13", "thermal", 8, "Run exchanger performance test", "The exchanger itself meets its clean reference."),
        ("T14", "sensors", 1, "Compare temperature sensors", "Sensors agree within tolerance."),
        ("T15", "maintenance", 1, "Read pump service note", "Pump bearings were replaced six months ago."),
        ("T16", "maintenance", 3, "Read valve service note", "The bypass actuator was serviced yesterday; mechanical travel was not verified."),
        ("T17", "operations", 1, "Check process load", "Load is stable and below maximum."),
        ("T18", "operations", 3, "Review fault onset", "Cooling loss began during the first valve movement after servicing."),
        ("T19", "ambient", 1, "Read ambient temperature", "Ambient temperature is ordinary."),
        ("T20", "records", 3, "Compare pump curve", "Measured pump head and total flow remain on the expected curve."),
    ]
    return FaultTask("eng-trap-001", "coordination_trap", "hard", _briefing("Vela habitat"), CANDIDATES, "bypass_valve_stuck_open", _items(rows))
