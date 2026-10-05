"""Safety incident database operations: add, search, filter, categorise, count, trend."""
import pandas as pd


def filter_incidents(df, start=None, end=None, department=None, shift=None, incident_type=None,
                     severity=None, status=None, location=None):
    """Apply any combination of filters; None / empty list means 'no filter'."""
    out = df
    if start is not None:
        out = out[out["date"] >= pd.Timestamp(start)]
    if end is not None:
        out = out[out["date"] <= pd.Timestamp(end)]
    for col, val in (("department", department), ("shift", shift), ("incident_type", incident_type),
                     ("severity", severity), ("status", status), ("location", location)):
        if val:
            vals = [val] if isinstance(val, str) else list(val)
            out = out[out[col].isin(vals)]
    return out


def search_incidents(df, query):
    """Case-insensitive text search across all text columns."""
    q = (query or "").strip().lower()
    if not q:
        return df
    text = df.astype(str).apply(lambda col: col.str.lower())
    mask = text.apply(lambda row: row.str.contains(q, regex=False).any(), axis=1)
    return df[mask]


def count_by(df, column):
    if df.empty:
        return pd.DataFrame({column: [], "count": []})
    out = df[column].value_counts().rename_axis(column).reset_index(name="count")
    return out


def categorise(df):
    """Cross-tabulation of incident type by severity."""
    if df.empty:
        return pd.DataFrame()
    return pd.crosstab(df["incident_type"], df["severity"], margins=True, margins_name="Total")


def monthly_trend(df):
    if df.empty:
        return pd.DataFrame({"month": [], "incidents": []})
    s = df.set_index("date").resample("MS").size().rename("incidents").reset_index()
    s["month"] = s["date"].dt.strftime("%Y-%m")
    return s[["month", "incidents"]]


def high_or_critical(df):
    return df[df["severity"].isin(["Major", "Critical"])]


def next_incident_id(df, year):
    nums = [int(i.split("-")[-1]) for i in df["incident_id"] if f"-{year}-" in i]
    return f"INC-{year}-{(max(nums) + 1 if nums else 1):04d}"


def shift_from_time(hhmm):
    """Day shift 06:00-17:59, Night shift otherwise."""
    return "Day" if 6 <= int(hhmm.split(":")[0]) < 18 else "Night"
