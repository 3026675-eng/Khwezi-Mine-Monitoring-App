"""Load / save CSV data and build the enriched 'Bundle' used by the app."""
from dataclasses import dataclass
from datetime import date

import pandas as pd

from . import alerts as alerts_mod
from . import config as C
from . import equipment as eq
from . import safety


@dataclass
class Bundle:
    workers: pd.DataFrame
    incidents: pd.DataFrame
    equipment: pd.DataFrame
    alerts: pd.DataFrame
    ref_date: date


def read_workers():
    return pd.read_csv(C.FILES["workers"])


def read_incidents():
    df = pd.read_csv(C.FILES["incidents"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def read_equipment():
    df = pd.read_csv(C.FILES["equipment"])
    for col in ("last_service_date", "next_service_due"):
        df[col] = pd.to_datetime(df[col])
    return df


def save(name, df):
    out = df.copy()
    for col in out.columns:
        if str(out[col].dtype).startswith("datetime"):
            out[col] = out[col].dt.strftime("%Y-%m-%d")
    out.to_csv(C.FILES[name], index=False)


def build_bundle(ref_date=None):
    ref_date = ref_date or date.today()
    workers = safety.enrich_workers(read_workers())
    incidents = read_incidents()
    equipment = eq.enrich_equipment(read_equipment(), ref_date)
    alerts = alerts_mod.generate_alerts(workers, incidents, equipment)
    return Bundle(workers, incidents, equipment, alerts, ref_date)


def kpis(b, role=None):
    """Dashboard KPIs, restricted to what the role is allowed to see."""
    can = lambda f: role is None or role in C.PERMISSIONS[f]
    out = {}
    if can("worker_safety"):
        w = b.workers
        out["Total workers"] = len(w)
        out["PPE compliance (%)"] = float(safety.ppe_compliance_rate(w))
        out["Near misses"] = int(w["near_misses"].sum())
        out["High-risk observations"] = int(w["risk_class"].isin(["High", "Critical"]).sum())
    if can("incidents"):
        out["Total safety incidents"] = len(b.incidents)
        out["Open critical incidents"] = int(((b.incidents["severity"] == "Critical") & (b.incidents["status"] != "Closed")).sum())
    if can("equipment"):
        e = b.equipment
        out["Total equipment"] = len(e)
        out["Equipment available"] = int((e["maintenance_status"] == "Operational").sum())
        out["Under maintenance"] = int((e["maintenance_status"] == "Under Maintenance").sum())
        out["Average availability (%)"] = float(round(e["availability"].mean(), 1)) if len(e) else 0.0
        out["Equipment alerts"] = int((b.alerts["category"].isin(["Equipment", "Maintenance"])).sum()) if len(b.alerts) else 0
        out["Critical equipment alerts"] = int(((b.alerts["category"] == "Equipment") & (b.alerts["severity"] == "CRITICAL")).sum()) if len(b.alerts) else 0
    return out
