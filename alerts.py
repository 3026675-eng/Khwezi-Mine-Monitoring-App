"""Automatic alert generation from predefined conditions."""
import pandas as pd

from . import config as C

COLUMNS = ["severity", "category", "entity_type", "entity_id", "area", "parameter", "value",
           "status", "recommended_action"]
ACTION_EQUIP = "Inspect equipment and initiate appropriate maintenance/safety procedures."


def _a(sev, cat, etype, eid, area, param, value, status, action):
    return dict(severity=sev, category=cat, entity_type=etype, entity_id=eid, area=area,
                parameter=param, value=value, status=status, recommended_action=action)


def generate_alerts(workers, incidents, equipment):
    """Return a DataFrame of active alerts. Inputs must already be enriched."""
    rows = []
    # ---- Equipment condition ----
    for _, r in equipment.iterrows():
        eid, area = r["equipment_id"], r["department"]
        if r["temp_status"] != "NORMAL":
            crit = r["temp_status"] == "CRITICAL"
            rows.append(_a(r["temp_status"], "Equipment", "Equipment", eid, area, "Temperature",
                           f"{r['temperature']:.1f} deg C",
                           "Above Critical Threshold" if crit else "Approaching Critical Threshold",
                           ACTION_EQUIP if crit else "Monitor closely and schedule an inspection."))
        if r["vib_status"] != "NORMAL":
            crit = r["vib_status"] == "CRITICAL"
            rows.append(_a(r["vib_status"], "Equipment", "Equipment", eid, area, "Vibration",
                           f"{r['vibration']:.1f} mm/s",
                           "Above Critical Threshold" if crit else "Approaching Critical Threshold",
                           ACTION_EQUIP if crit else "Monitor closely and schedule an inspection."))
        for col, label in (("brake_status", "Brake"), ("tyre_status", "Tyre"), ("engine_status", "Engine")):
            s = {"Fault": "CRITICAL", "Worn": "WARNING"}.get(r[col])
            if s:
                rows.append(_a(s, "Equipment", "Equipment", eid, area, f"{label} status", r[col],
                               "Fault detected" if s == "CRITICAL" else "Wear detected",
                               ACTION_EQUIP if s == "CRITICAL" else "Plan component replacement."))
        # ---- Maintenance ----
        if r["maintenance_state"] == "Overdue":
            rows.append(_a("WARNING", "Maintenance", "Equipment", eid, area, "Scheduled service",
                           str(r["next_service_due"].date()), "Overdue maintenance",
                           "Schedule the overdue service immediately."))
        if r["excessive_downtime"]:
            rows.append(_a("WARNING", "Maintenance", "Equipment", eid, area, "Downtime",
                           f"{r['downtime_hours']:.0f} h", f"Above {C.EXCESSIVE_DOWNTIME_H:.0f} h limit",
                           "Investigate root cause of downtime."))
        if r["low_availability"]:
            rows.append(_a("WARNING", "Maintenance", "Equipment", eid, area, "Availability",
                           f"{r['availability']:.1f} %", f"Below {C.LOW_AVAILABILITY:.0f} % target",
                           "Review maintenance strategy for this unit."))
        if r["repeated_alerts"]:
            rows.append(_a("WARNING", "Maintenance", "Equipment", eid, area, "Repeated alerts",
                           f"{int(r['alerts_30d'])} in 30 days", f"At or above {C.REPEATED_ALERTS}",
                           "Perform a reliability review."))
    # ---- Worker safety ----
    for _, r in workers.iterrows():
        wid, area = r["worker_id"], r["department"]
        if r["ppe_compliant"] != "Yes":
            rows.append(_a("WARNING", "Worker Safety", "Worker", wid, area, "PPE compliance",
                           "Non-compliant", "Low PPE compliance", "Supervisor to correct PPE before work continues."))
        if r["fatigue_level"] >= C.FATIGUE_WARNING:
            crit = r["fatigue_level"] >= C.FATIGUE_CRITICAL
            rows.append(_a("CRITICAL" if crit else "WARNING", "Worker Safety", "Worker", wid, area,
                           "Fatigue level", f"{r['fatigue_level']}/10", "High fatigue level",
                           "Remove from safety-critical tasks and arrange rest." if crit else "Supervisor check-in; consider task rotation."))
        if r["risk_class"] in ("High", "Critical"):
            rows.append(_a("CRITICAL" if r["risk_class"] == "Critical" else "WARNING", "Risk", "Worker",
                           wid, area, "Risk score", f"{r['risk_score']} ({r['risk_class']})",
                           "High-risk safety observation", "Review controls and update the risk register."))
    # ---- Incidents ----
    if len(incidents):
        crit = incidents[(incidents["severity"] == "Critical") & (incidents["status"] != "Closed")]
        for _, r in crit.iterrows():
            rows.append(_a("CRITICAL", "Incident", "Incident", r["incident_id"], r["department"],
                           "Incident severity", f"{r['incident_type']} ({r['severity']})",
                           f"Status: {r['status']}", "Complete investigation and implement corrective action."))
    # ---- Department-level PPE compliance ----
    if len(workers):
        for dept, g in workers.groupby("department"):
            rate = (g["ppe_compliant"] == "Yes").mean() * 100
            if rate < C.PPE_TARGET:
                rows.append(_a("WARNING", "Worker Safety", "Department", dept, dept, "Dept PPE compliance",
                               f"{rate:.1f} %", f"Below {C.PPE_TARGET:.0f} % target", "Run a PPE compliance campaign."))
    out = pd.DataFrame(rows, columns=COLUMNS)
    if out.empty:
        return out
    out["_o"] = out["severity"].map({"CRITICAL": 0, "WARNING": 1})
    out = out.sort_values(["_o", "category", "entity_id"]).drop(columns="_o").reset_index(drop=True)
    out.insert(0, "alert_id", [f"ALT-{i + 1:03d}" for i in range(len(out))])
    return out


def filter_by_permissions(alerts, role):
    allowed = [c for c, p in C.ALERT_PERMISSION.items() if role in C.PERMISSIONS[p]]
    return alerts[alerts["category"].isin(allowed)] if len(alerts) else alerts


def format_alert_text(a):
    """Plain-text alert in the format of Figure 1 of the brief."""
    bar = "=" * 53
    return "\n".join([
        bar, "MINING MONITORING ALERT", bar, f"[{a['severity']}]",
        f"{a['entity_type']} ID: {a['entity_id']}", f"Parameter: {a['parameter']}",
        f"Value: {a['value']}", f"Status: {a['status']}", "Recommended Action:",
        f" {a['recommended_action']}", bar,
    ])
