"""Interactive data analysis: Appendix A business questions implemented with pandas.

Each question is a function  fn(bundle, ctx) -> Answer  where ctx carries the selected period.
"""
from dataclasses import dataclass, field
from typing import Callable, Optional

import pandas as pd

from . import config as C
from . import incidents as inc
from . import safety


@dataclass
class Answer:
    text: str
    table: Optional[pd.DataFrame] = None
    chart: Optional[dict] = None          # {"kind": "bar|line|pie", "x": col, "y": col, "title": str}


@dataclass
class Question:
    qid: str
    group: str
    text: str
    requires: set
    fn: Callable = field(repr=False)


@dataclass
class Ctx:
    start: object = None
    end: object = None


def _inc(b, ctx):
    return inc.filter_incidents(b.incidents, ctx.start, ctx.end)


def _top(df, col, label):
    if df.empty:
        return "no data"
    row = df.iloc[0]
    return f"{row[col]} ({row[label]})"


# ------------------------------ Health & safety ------------------------------
def h1(b, ctx):
    d = _inc(b, ctx)
    return Answer(f"{len(d)} safety incidents were recorded in the selected period.",
                  inc.monthly_trend(d), {"kind": "line", "x": "month", "y": "incidents", "title": "Incidents per month"})


def h2(b, ctx):
    t = inc.count_by(_inc(b, ctx), "department")
    return Answer(f"{t.iloc[0]['department']} has the highest number of incidents ({t.iloc[0]['count']})." if len(t) else "No incidents in period.",
                  t, {"kind": "bar", "x": "department", "y": "count", "title": "Incidents by department"})


def h3(b, ctx):
    t = inc.count_by(_inc(b, ctx), "shift")
    return Answer(f"The {t.iloc[0]['shift']} shift records the most incidents ({t.iloc[0]['count']})." if len(t) else "No incidents in period.",
                  t, {"kind": "bar", "x": "shift", "y": "count", "title": "Incidents by shift"})


def h4(b, ctx):
    w = b.workers
    rate = safety.ppe_compliance_rate(w)
    t = safety.department_summary(w)[["department", "ppe_compliance_%"]].sort_values("ppe_compliance_%")
    return Answer(f"{rate}% of workers comply with PPE requirements ({int((w['ppe_compliant'] == 'No').sum())} non-compliant). "
                  f"Target: {C.PPE_TARGET:.0f}%.", t, {"kind": "bar", "x": "department", "y": "ppe_compliance_%", "title": "PPE compliance by department (%)"})


def h5(b, ctx):
    w = b.workers
    t = w.groupby("department")["near_misses"].sum().reset_index().sort_values("near_misses", ascending=False)
    return Answer(f"{int(w['near_misses'].sum())} near misses have been recorded.", t,
                  {"kind": "bar", "x": "department", "y": "near_misses", "title": "Near misses by department"})


def h6(b, ctx):
    t = inc.count_by(_inc(b, ctx), "incident_type")
    return Answer(f"The most frequent incident type is {t.iloc[0]['incident_type']} ({t.iloc[0]['count']})." if len(t) else "No incidents in period.",
                  t, {"kind": "bar", "x": "incident_type", "y": "count", "title": "Incidents by type"})


def h7(b, ctx):
    d = _inc(b, ctx)
    hc = inc.high_or_critical(d)
    t = inc.count_by(hc, "severity")
    return Answer(f"{len(hc)} incidents ({(len(hc) / len(d) * 100 if len(d) else 0):.1f}% of the period) are classified Major or Critical.",
                  t, {"kind": "pie", "x": "severity", "y": "count", "title": "Major / Critical incidents"})


def h8(b, ctx):
    t = safety.department_summary(b.workers).sort_values("avg_risk_score", ascending=False)
    return Answer(f"{t.iloc[0]['department']} has the highest average risk score ({t.iloc[0]['avg_risk_score']}).",
                  t[["department", "avg_risk_score", "high_or_critical", "workers"]],
                  {"kind": "bar", "x": "department", "y": "avg_risk_score", "title": "Average risk score by department"})


def h9(b, ctx):
    d = _inc(b, ctx)
    t = inc.count_by(d, "shift")
    if t.empty or set(t["shift"]) != set(C.SHIFTS):
        return Answer("Not enough data to compare shifts.", t)
    day, night = [int(t.loc[t["shift"] == s, "count"].iloc[0]) for s in C.SHIFTS]
    diff = (night - day) / day * 100 if day else float("nan")
    word = "more" if night > day else "fewer"
    return Answer(f"Day: {day} incidents, Night: {night}. Night shift has {abs(diff):.1f}% {word} incidents than day shift "
                  "(observed difference only, not a statistical test).",
                  t, {"kind": "bar", "x": "shift", "y": "count", "title": "Day vs night incidents"})


def h10(b, ctx):
    u = safety.unsafe_workers(b.workers)
    crit = u[u["worst"] == "CRITICAL"]
    openc = b.incidents[(b.incidents["severity"] == "Critical") & (b.incidents["status"] != "Closed")]
    return Answer(f"{len(crit)} workers have CRITICAL conditions and {len(openc)} critical incidents are still open - these need immediate attention.",
                  crit[["worker_id", "department", "shift", "warnings"]].head(25))


# --------------------------------- Equipment ---------------------------------
def _eq_rank(b, col, label, ascending=False, fmt=""):
    t = b.equipment.sort_values(col, ascending=ascending)[["equipment_id", "equipment_type", col]].head(10)
    top = t.iloc[0]
    return Answer(f"{top['equipment_id']} ({top['equipment_type']}) has the {label}: {top[col]}{fmt}.", t,
                  {"kind": "bar", "x": "equipment_id", "y": col, "title": f"Top 10 by {label}"})


def e1(b, ctx): return _eq_rank(b, "downtime_hours", "highest downtime", False, " h")
def e2(b, ctx): return _eq_rank(b, "availability", "lowest availability", True, " %")
def e3(b, ctx): return _eq_rank(b, "vibration", "highest vibration", False, " mm/s")
def e4(b, ctx): return _eq_rank(b, "temperature", "highest operating temperature", False, " deg C")
def e5(b, ctx): return _eq_rank(b, "alerts_30d", "most alerts (30 days)", False, " alerts")


def e6(b, ctx):
    e = b.equipment
    need = e[e["maintenance_state"].isin(["Due Soon", "Overdue"]) | (e["condition"] == "CRITICAL")]
    return Answer(f"{len(need)} units require maintenance (due soon, overdue or in critical condition).",
                  need[["equipment_id", "equipment_type", "maintenance_state", "condition", "next_service_due"]].sort_values("maintenance_state"))


def e7(b, ctx):
    o = b.equipment[b.equipment["maintenance_state"] == "Overdue"].copy()
    o["days_overdue"] = (pd.Timestamp(b.ref_date) - o["next_service_due"]).dt.days
    return Answer(f"{len(o)} units are overdue for maintenance.",
                  o[["equipment_id", "equipment_type", "next_service_due", "days_overdue"]].sort_values("days_overdue", ascending=False),
                  {"kind": "bar", "x": "equipment_id", "y": "days_overdue", "title": "Days overdue"} if len(o) else None)


def e8(b, ctx):
    e = b.equipment
    t = e.groupby("equipment_type")["availability"].mean().round(1).reset_index().sort_values("availability")
    return Answer(f"Average equipment availability is {e['availability'].mean():.1f}% (target {C.LOW_AVAILABILITY:.0f}%+).", t,
                  {"kind": "bar", "x": "equipment_type", "y": "availability", "title": "Average availability by type (%)"})


def e9(b, ctx):
    t = b.equipment.groupby("equipment_type")["downtime_hours"].sum().round(1).reset_index().sort_values("downtime_hours", ascending=False)
    return Answer(f"{t.iloc[0]['equipment_type']} has the highest total downtime ({t.iloc[0]['downtime_hours']} h).", t,
                  {"kind": "bar", "x": "equipment_type", "y": "downtime_hours", "title": "Total downtime by equipment type (h)"})


def e10(b, ctx):
    e = b.equipment
    crit = e[e["condition"] == "CRITICAL"]
    return Answer(f"{len(crit)} units are in CRITICAL condition and need immediate inspection.",
                  crit[["equipment_id", "equipment_type", "temperature", "vibration", "condition_message"]])


# ---------------------------- Integrated analysis ----------------------------
def i1(b, ctx):
    d = _inc(b, ctx)
    if d.empty:
        return Answer("No incidents in period.")
    t = pd.crosstab(d["shift"], d["severity"]).reset_index()
    share = d.groupby("shift")["severity"].apply(lambda s: s.isin(["Major", "Critical"]).mean() * 100).round(1)
    return Answer("Incidents by shift and severity. Share of Major/Critical: " + ", ".join(f"{k}: {v}%" for k, v in share.items()) + ".", t)


def i2(b, ctx):
    ds = safety.department_summary(b.workers).set_index("department")
    dt = b.equipment.groupby("department")["downtime_hours"].sum().rename("equipment_downtime_h")
    t = ds[["avg_risk_score", "high_or_critical"]].join(dt, how="outer").fillna(0).reset_index()
    hi = t[(t["avg_risk_score"] >= t["avg_risk_score"].median()) & (t["equipment_downtime_h"] >= t["equipment_downtime_h"].median())]
    names = ", ".join(hi["department"]) or "none"
    return Answer(f"Departments above the median on BOTH risk score and equipment downtime: {names}.",
                  t.sort_values("equipment_downtime_h", ascending=False),
                  {"kind": "bar", "x": "department", "y": "equipment_downtime_h", "title": "Equipment downtime by department (h)"})


def i3(b, ctx):
    a = b.alerts[b.alerts["entity_type"] == "Equipment"] if len(b.alerts) else b.alerts
    if a.empty:
        return Answer("No active equipment alerts.")
    t = a.groupby("entity_id").size().rename("active_alerts").reset_index().sort_values("active_alerts", ascending=False).head(10)
    return Answer(f"{t.iloc[0]['entity_id']} contributes the most active alerts ({t.iloc[0]['active_alerts']}).", t,
                  {"kind": "bar", "x": "entity_id", "y": "active_alerts", "title": "Active alerts per equipment"})


def i4(b, ctx):
    t = b.equipment.sort_values("priority_score", ascending=False)[
        ["equipment_id", "equipment_type", "priority_score", "condition", "maintenance_state", "availability"]].head(10)
    return Answer(f"Maintenance priority #1: {t.iloc[0]['equipment_id']} (priority score {t.iloc[0]['priority_score']}). "
                  "Score = condition (0/1/3) + service state (0/1/3) + low availability (2) + excessive downtime (1) + repeated alerts (1).",
                  t, {"kind": "bar", "x": "equipment_id", "y": "priority_score", "title": "Maintenance priority score"})


def i5(b, ctx):
    t = inc.count_by(_inc(b, ctx), "cause")
    return Answer(f"The most common cause of incidents is '{t.iloc[0]['cause']}' ({t.iloc[0]['count']})." if len(t) else "No incidents in period.",
                  t, {"kind": "bar", "x": "cause", "y": "count", "title": "Incident causes"})


def i6(b, ctx):
    w, d = b.workers, b.incidents
    rows = [("PPE compliance %", safety.ppe_compliance_rate(w), f"< {C.PPE_TARGET:.0f}", safety.ppe_compliance_rate(w) < C.PPE_TARGET),
            ("Workers with severe fatigue", int((w["fatigue_level"] >= C.FATIGUE_CRITICAL).sum()), "> 0", (w["fatigue_level"] >= C.FATIGUE_CRITICAL).any()),
            ("Expired safety training", int((w["training_status"] == "Expired").sum()), "> 0", (w["training_status"] == "Expired").any()),
            ("High/critical risk workers", int(w["risk_class"].isin(["High", "Critical"]).sum()), "> 0", w["risk_class"].isin(["High", "Critical"]).any()),
            ("Open critical incidents", int(((d["severity"] == "Critical") & (d["status"] != "Closed")).sum()), "> 0",
             ((d["severity"] == "Critical") & (d["status"] != "Closed")).any())]
    t = pd.DataFrame(rows, columns=["indicator", "value", "intervene_when", "needs_intervention"])
    return Answer(f"{int(t['needs_intervention'].sum())} of {len(t)} safety indicators require management intervention.", t)


def i7(b, ctx):
    e = b.equipment
    pct = (e["condition"] == "NORMAL").mean() * 100 if len(e) else 0
    t = e["condition"].value_counts().rename_axis("condition").reset_index(name="count")
    return Answer(f"{pct:.1f}% of monitored equipment is operating normally.", t,
                  {"kind": "pie", "x": "condition", "y": "count", "title": "Equipment condition"})


def i8(b, ctx):
    a = b.alerts
    n = int((a["severity"] == "CRITICAL").sum()) if len(a) else 0
    t = a[a["severity"] == "CRITICAL"].groupby("category").size().rename("critical_alerts").reset_index() if n else None
    return Answer(f"{n} critical alerts are currently active.", t,
                  {"kind": "bar", "x": "category", "y": "critical_alerts", "title": "Critical alerts by category"} if n else None)


def _attention(b):
    ds = safety.department_summary(b.workers).set_index("department")
    out = pd.DataFrame(index=C.DEPARTMENTS)
    out["high_risk_workers"] = ds["high_or_critical"]
    out["ppe_gap_%"] = (100 - ds["ppe_compliance_%"]).round(1)
    out["incidents"] = b.incidents.groupby("department").size()
    out["critical_equipment"] = b.equipment[b.equipment["condition"] == "CRITICAL"].groupby("department").size()
    out["overdue_equipment"] = b.equipment[b.equipment["maintenance_state"] == "Overdue"].groupby("department").size()
    out = out.fillna(0)
    # rank-sum so no single scale dominates
    out["attention_score"] = out.rank(pct=True).sum(axis=1).round(2)
    return out.sort_values("attention_score", ascending=False).reset_index().rename(columns={"index": "department"})


def i9(b, ctx):
    t = _attention(b)
    return Answer(f"{t.iloc[0]['department']} needs the greatest attention (highest combined safety + equipment rank).", t,
                  {"kind": "bar", "x": "department", "y": "attention_score", "title": "Attention score by department"})


def recommendations(b):
    recs = []
    w, e, d = b.workers, b.equipment, b.incidents
    rate = safety.ppe_compliance_rate(w)
    if rate < C.PPE_TARGET:
        recs.append(f"PPE compliance is {rate}% (target {C.PPE_TARGET:.0f}%): run supervisor-led PPE checks at shift start.")
    sev_f = int((w["fatigue_level"] >= C.FATIGUE_CRITICAL).sum())
    if sev_f:
        recs.append(f"{sev_f} workers report severe fatigue: review rosters and rest breaks, especially on night shift.")
    exp = int((w["training_status"] == "Expired").sum())
    if exp:
        recs.append(f"{exp} workers have expired safety training: schedule refresher training before the next roster.")
    oc = int(((d["severity"] == "Critical") & (d["status"] != "Closed")).sum())
    if oc:
        recs.append(f"{oc} critical incidents remain open: complete investigations and close out corrective actions.")
    crit = e[e["condition"] == "CRITICAL"]["equipment_id"].tolist()
    if crit:
        recs.append(f"Inspect critical-condition equipment immediately: {', '.join(crit[:8])}{'...' if len(crit) > 8 else ''}.")
    ov = int((e["maintenance_state"] == "Overdue").sum())
    if ov:
        recs.append(f"{ov} units are overdue for service: re-plan the maintenance schedule starting with the highest priority scores.")
    la = e[e["low_availability"]]["equipment_id"].tolist()
    if la:
        recs.append(f"Low availability on {len(la)} units ({', '.join(la[:6])}{'...' if len(la) > 6 else ''}): investigate root causes of downtime.")
    ti = inc.count_by(d, "incident_type")
    if len(ti):
        recs.append(f"The most frequent incident type is {ti.iloc[0]['incident_type']}: target it in the next safety campaign.")
    return recs or ["No immediate interventions identified."]


def i10(b, ctx):
    recs = recommendations(b)
    return Answer("Generated recommendations:\n" + "\n".join(f"{i + 1}. {r}" for i, r in enumerate(recs)),
                  pd.DataFrame({"recommendation": recs}))


QUESTIONS = [
    Question("H1", "Health and Safety", "How many safety incidents occurred during the selected period?", {"incidents"}, h1),
    Question("H2", "Health and Safety", "Which department has the highest number of incidents?", {"incidents"}, h2),
    Question("H3", "Health and Safety", "Which shift records the most incidents?", {"incidents"}, h3),
    Question("H4", "Health and Safety", "What percentage of workers comply with PPE requirements?", {"worker_safety"}, h4),
    Question("H5", "Health and Safety", "How many near misses have been recorded?", {"worker_safety"}, h5),
    Question("H6", "Health and Safety", "Which incident types occur most frequently?", {"incidents"}, h6),
    Question("H7", "Health and Safety", "How many incidents are classified as high or critical?", {"incidents"}, h7),
    Question("H8", "Health and Safety", "Which departments have the highest safety risk?", {"worker_safety", "risk"}, h8),
    Question("H9", "Health and Safety", "Is there an observable difference in incidents between day and night shifts?", {"incidents"}, h9),
    Question("H10", "Health and Safety", "Which safety conditions require immediate attention?", {"worker_safety", "incidents"}, h10),
    Question("E1", "Equipment", "Which equipment has the highest downtime?", {"equipment"}, e1),
    Question("E2", "Equipment", "Which equipment has the lowest availability?", {"equipment"}, e2),
    Question("E3", "Equipment", "Which equipment has the highest vibration?", {"equipment"}, e3),
    Question("E4", "Equipment", "Which equipment has the highest operating temperature?", {"equipment"}, e4),
    Question("E5", "Equipment", "Which equipment has generated the most alerts?", {"equipment"}, e5),
    Question("E6", "Equipment", "Which equipment requires maintenance?", {"maintenance"}, e6),
    Question("E7", "Equipment", "Which equipment is overdue for maintenance?", {"maintenance"}, e7),
    Question("E8", "Equipment", "What is the average equipment availability?", {"equipment"}, e8),
    Question("E9", "Equipment", "Which equipment type has the highest downtime?", {"equipment"}, e9),
    Question("E10", "Equipment", "Which equipment requires immediate inspection?", {"equipment"}, e10),
    Question("I1", "Integrated", "Are safety incidents associated with particular shifts?", {"incidents"}, i1),
    Question("I2", "Integrated", "Which departments have both high safety risk and high equipment downtime?", {"worker_safety", "equipment"}, i2),
    Question("I3", "Integrated", "Which equipment contributes to the greatest number of alerts?", {"equipment"}, i3),
    Question("I4", "Integrated", "Which equipment should receive maintenance priority?", {"maintenance"}, i4),
    Question("I5", "Integrated", "What are the most common causes of safety incidents?", {"incidents"}, i5),
    Question("I6", "Integrated", "Which safety indicators require management intervention?", {"worker_safety", "incidents"}, i6),
    Question("I7", "Integrated", "What percentage of monitored equipment is operating normally?", {"equipment"}, i7),
    Question("I8", "Integrated", "How many critical alerts are currently active?", {"worker_safety", "incidents", "equipment"}, i8),
    Question("I9", "Integrated", "Which areas of the operation require the greatest attention?", {"worker_safety", "incidents", "equipment"}, i9),
    Question("I10", "Integrated", "What recommendations can be generated from the monitoring results?", {"worker_safety", "incidents", "equipment"}, i10),
]


def available_questions(role):
    """Questions whose required permissions are all held by the role."""
    return [q for q in QUESTIONS if all(role in C.PERMISSIONS[p] for p in q.requires)]
