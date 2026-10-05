"""Report generation (plain text + CSV) - content is restricted to what the role may see."""
from datetime import datetime

from . import analysis as an
from . import config as C
from . import data_loader as dl
from . import equipment as eq
from . import safety


def build_text_report(b, role, username):
    can = lambda f: role in C.PERMISSIONS[f]
    L = ["=" * 60, "KHWEZI MINING - HEALTH, SAFETY AND EQUIPMENT MONITORING REPORT", "=" * 60,
         f"Generated: {datetime.now():%Y-%m-%d %H:%M}   User: {username} ({role})",
         f"Reference date: {b.ref_date}", "", "KEY PERFORMANCE INDICATORS", "-" * 30]
    L += [f"  {k}: {v}" for k, v in dl.kpis(b, role).items()]
    if can("worker_safety"):
        u = safety.unsafe_workers(b.workers)
        L += ["", "WORKER SAFETY", "-" * 30, f"  Workers with warnings: {len(u)} (critical: {int((u['worst'] == 'CRITICAL').sum())})"]
    if can("maintenance"):
        L += ["", "MAINTENANCE", "-" * 30]
        for name, df in eq.maintenance_lists(b.equipment).items():
            L.append(f"  {name}: {len(df)}" + (f"  [{', '.join(df['equipment_id'].head(8))}]" if len(df) else ""))
    from . import alerts as al
    a = al.filter_by_permissions(b.alerts, role)
    L += ["", "ACTIVE ALERTS", "-" * 30, f"  Total: {len(a)}   Critical: {int((a['severity'] == 'CRITICAL').sum()) if len(a) else 0}"]
    if can("worker_safety") and can("incidents") and can("equipment"):
        L += ["", "RECOMMENDATIONS", "-" * 30] + [f"  {i + 1}. {r}" for i, r in enumerate(an.recommendations(b))]
    L += ["", "NOTE: thresholds are educational prototype values, not statutory or manufacturer limits."]
    return "\n".join(L)


def downloadable_tables(b, role):
    """name -> DataFrame for every table the role is allowed to export."""
    from . import alerts as al
    out = {"alerts": al.filter_by_permissions(b.alerts, role)}
    if role in C.PERMISSIONS["worker_safety"]:
        out["workers"] = b.workers
    if role in C.PERMISSIONS["incidents"]:
        out["incidents"] = b.incidents
    if role in C.PERMISSIONS["equipment"]:
        out["equipment"] = b.equipment
    return out
