"""Worker health and safety monitoring."""
import pandas as pd

from . import config as C
from . import risk


def enrich_workers(df):
    df = df.copy()
    if df.empty:
        df["risk_score"], df["risk_class"] = [], []
        return df
    df["risk_score"] = [risk.risk_score(l, c) for l, c in zip(df["likelihood"], df["consequence"])]
    df["risk_class"] = df["risk_score"].map(risk.classify_risk)
    return df


def ppe_compliance_rate(df):
    return 0.0 if df.empty else round((df["ppe_compliant"] == "Yes").mean() * 100, 1)


def worker_warnings(row):
    """List of (severity, text) warnings for one worker."""
    w = []
    if row["ppe_compliant"] != "Yes":
        w.append(("WARNING", "PPE non-compliant"))
    if row["training_status"] == "Expired":
        w.append(("WARNING", "Safety training expired"))
    if row["fatigue_level"] >= C.FATIGUE_CRITICAL:
        w.append(("CRITICAL", f"Severe fatigue ({row['fatigue_level']}/10)"))
    elif row["fatigue_level"] >= C.FATIGUE_WARNING:
        w.append(("WARNING", f"High fatigue ({row['fatigue_level']}/10)"))
    if row["near_misses"] >= C.NEAR_MISS_LIMIT:
        w.append(("WARNING", f"{row['near_misses']} near misses"))
    if row["previous_incidents"] >= C.PREVIOUS_INCIDENT_LIMIT:
        w.append(("WARNING", f"{row['previous_incidents']} previous incidents"))
    if row["risk_class"] == "Critical":
        w.append(("CRITICAL", f"Critical risk (score {row['risk_score']})"))
    elif row["risk_class"] == "High":
        w.append(("WARNING", f"High risk (score {row['risk_score']})"))
    return w


def unsafe_workers(df):
    """Workers with at least one warning, most serious first."""
    if df.empty:
        return df.assign(warnings=[], warning_count=[], worst=[])
    out = df.copy()
    ws = out.apply(worker_warnings, axis=1)
    out["warnings"] = ws.map(lambda lst: "; ".join(t for _, t in lst))
    out["warning_count"] = ws.map(len)
    out["worst"] = ws.map(lambda lst: "CRITICAL" if any(s == "CRITICAL" for s, _ in lst) else ("WARNING" if lst else "OK"))
    out = out[out["warning_count"] > 0]
    out["_o"] = out["worst"].map({"CRITICAL": 0, "WARNING": 1})
    return out.sort_values(["_o", "warning_count", "risk_score"], ascending=[True, False, False]).drop(columns="_o")


def department_summary(df):
    if df.empty:
        return pd.DataFrame()
    g = df.groupby("department")
    return pd.DataFrame({
        "workers": g.size(),
        "ppe_compliance_%": g["ppe_compliant"].apply(lambda s: round((s == "Yes").mean() * 100, 1)),
        "avg_fatigue": g["fatigue_level"].mean().round(1),
        "near_misses": g["near_misses"].sum(),
        "avg_risk_score": g["risk_score"].mean().round(1),
        "high_or_critical": g["risk_class"].apply(lambda s: int(s.isin(["High", "Critical"]).sum())),
    }).reset_index()


def next_worker_id(df):
    nums = [int(i[1:]) for i in df["worker_id"]] if len(df) else [0]
    return f"W{max(nums) + 1:03d}"
