"""Equipment condition monitoring and maintenance monitoring."""
from datetime import timedelta

import pandas as pd

from . import config as C

ORDER = {"NORMAL": 0, "WARNING": 1, "CRITICAL": 2}


def availability(operating, downtime):
    """Availability = Operating / (Operating + Downtime) x 100 (0 if no time recorded)."""
    total = operating + downtime
    return 0.0 if total <= 0 else operating / total * 100.0


def classify(value, warning, critical):
    """<warning NORMAL, warning..critical (inclusive) WARNING, >critical CRITICAL."""
    if value < warning:
        return "NORMAL"
    return "WARNING" if value <= critical else "CRITICAL"


def temperature_status(t):
    return classify(t, C.TEMP_WARNING, C.TEMP_CRITICAL)


def vibration_status(v):
    return classify(v, C.VIB_WARNING, C.VIB_CRITICAL)


def component_status(value):
    return {"Fault": "CRITICAL", "Worn": "WARNING"}.get(value, "NORMAL")


def condition_report(row):
    """Return (overall_status, [messages]) for one equipment row."""
    findings = []  # (status, message)
    t, v = temperature_status(row["temperature"]), vibration_status(row["vibration"])
    if t == "WARNING":
        findings.append(("WARNING", "Equipment temperature approaching predefined threshold."))
    elif t == "CRITICAL":
        findings.append(("CRITICAL", "Equipment temperature exceeds predefined threshold. Inspection required"))
    if v == "WARNING":
        findings.append(("WARNING", "Equipment vibration approaching predefined threshold."))
    elif v == "CRITICAL":
        findings.append(("CRITICAL", "Equipment vibration exceeds predefined threshold. Inspection required"))
    for col, label in (("brake_status", "Brake"), ("tyre_status", "Tyre"), ("engine_status", "Engine")):
        s = component_status(row[col])
        if s != "NORMAL":
            findings.append((s, f"{label} status: {row[col]}."
                             + (" Inspection required" if s == "CRITICAL" else "")))
    if not findings:
        return "NORMAL", ["Equipment operating within defined monitoring limits."]
    overall = max((f[0] for f in findings), key=lambda s: ORDER[s])
    return overall, [f[1] for f in findings]


def maintenance_state(row, ref_date):
    if row["maintenance_status"] == "Under Maintenance":
        return "Under Maintenance"
    due = row["next_service_due"].date()
    if due < ref_date:
        return "Overdue"
    if due <= ref_date + timedelta(days=C.DUE_SOON_DAYS):
        return "Due Soon"
    return "OK"


def enrich_equipment(df, ref_date):
    """Add calculated monitoring columns. Does not modify the input frame."""
    df = df.copy()
    if df.empty:
        for col in ("availability", "temp_status", "vib_status", "condition", "condition_message",
                    "maintenance_state", "excessive_downtime", "low_availability",
                    "repeated_alerts", "priority_score"):
            df[col] = []
        return df
    df["availability"] = [round(availability(o, d), 1) for o, d in zip(df["uptime_hours"], df["downtime_hours"])]
    df["temp_status"] = df["temperature"].map(temperature_status)
    df["vib_status"] = df["vibration"].map(vibration_status)
    reports = df.apply(condition_report, axis=1)
    df["condition"] = [r[0] for r in reports]
    df["condition_message"] = [" ".join(r[1]) for r in reports]
    df["maintenance_state"] = df.apply(lambda r: maintenance_state(r, ref_date), axis=1)
    df["excessive_downtime"] = df["downtime_hours"] > C.EXCESSIVE_DOWNTIME_H
    df["low_availability"] = df["availability"] < C.LOW_AVAILABILITY
    df["repeated_alerts"] = df["alerts_30d"] >= C.REPEATED_ALERTS
    # Maintenance priority score (higher = more urgent)
    df["priority_score"] = (
        df["condition"].map({"NORMAL": 0, "WARNING": 1, "CRITICAL": 3})
        + df["maintenance_state"].map({"OK": 0, "Due Soon": 1, "Under Maintenance": 0, "Overdue": 3})
        + df["low_availability"].astype(int) * 2
        + df["excessive_downtime"].astype(int)
        + df["repeated_alerts"].astype(int)
    )
    return df


def maintenance_lists(df):
    """The six maintenance groupings required by the brief."""
    return {
        "Due for maintenance": df[df["maintenance_state"] == "Due Soon"],
        "Overdue": df[df["maintenance_state"] == "Overdue"],
        "Under maintenance": df[df["maintenance_state"] == "Under Maintenance"],
        "Excessive downtime": df[df["excessive_downtime"]],
        "Repeated alerts": df[df["repeated_alerts"]],
        "Low availability": df[df["low_availability"]],
    }


def next_equipment_id(df, equipment_type):
    prefix = C.EQUIPMENT_PREFIX[equipment_type]
    nums = [int(i.split("-")[1]) for i in df["equipment_id"] if i.startswith(prefix + "-")]
    return f"{prefix}-{(max(nums) + 1 if nums else 1):03d}"
