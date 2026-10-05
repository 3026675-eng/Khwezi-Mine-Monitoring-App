"""Input validation - prevents invalid data from crashing or corrupting the system."""
import re
from datetime import date, datetime

from . import config as C


def to_number(value, minimum=None, maximum=None, integer=False):
    """Return a number or None if value is not numeric / out of range."""
    try:
        num = float(str(value).strip())
    except (ValueError, TypeError):
        return None
    if num != num or num in (float("inf"), float("-inf")):
        return None
    if integer and num != int(num):
        return None
    if minimum is not None and num < minimum:
        return None
    if maximum is not None and num > maximum:
        return None
    return int(num) if integer else num


def validate_worker(rec, existing_ids=()):
    errs = []
    wid = str(rec.get("worker_id", "")).strip().upper()
    if not re.fullmatch(r"W\d{3,4}", wid):
        errs.append("Worker ID must look like W001.")
    elif wid in set(existing_ids):
        errs.append(f"Worker ID {wid} already exists.")
    if rec.get("department") not in C.DEPARTMENTS:
        errs.append("Select a valid department.")
    if not str(rec.get("job_role", "")).strip():
        errs.append("Job role is required.")
    if rec.get("shift") not in C.SHIFTS:
        errs.append("Shift must be Day or Night.")
    if rec.get("ppe_compliant") not in ("Yes", "No"):
        errs.append("PPE compliance must be Yes or No.")
    if rec.get("training_status") not in C.TRAINING_STATUS:
        errs.append("Select a valid training status.")
    if to_number(rec.get("fatigue_level"), 1, 10, True) is None:
        errs.append("Fatigue level must be a whole number from 1 to 10.")
    for f in ("safety_observations", "near_misses", "previous_incidents"):
        if to_number(rec.get(f), 0, 1000, True) is None:
            errs.append(f"{f.replace('_', ' ').capitalize()} must be a whole number >= 0.")
    for f in ("likelihood", "consequence"):
        if to_number(rec.get(f), 1, 5, True) is None:
            errs.append(f"{f.capitalize()} must be a whole number from 1 to 5.")
    return errs


def validate_incident(rec):
    errs = []
    try:
        d = rec["date"] if isinstance(rec["date"], date) else datetime.strptime(str(rec["date"]), "%Y-%m-%d").date()
        if d > date.today():
            errs.append("Incident date cannot be in the future.")
    except (ValueError, KeyError):
        errs.append("Date must be in YYYY-MM-DD format.")
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", str(rec.get("time", ""))):
        errs.append("Time must be in HH:MM (24 hour) format.")
    for field, options in (("department", C.DEPARTMENTS), ("incident_type", C.INCIDENT_TYPES),
                           ("severity", C.SEVERITIES), ("injury_status", C.INJURY_STATUS),
                           ("status", C.INCIDENT_STATUS), ("location", C.LOCATIONS),
                           ("cause", C.CAUSES)):
        if rec.get(field) not in options:
            errs.append(f"Select a valid {field.replace('_', ' ')}.")
    if rec.get("lost_time_injury") not in ("Yes", "No"):
        errs.append("Lost-time injury must be Yes or No.")
    if rec.get("lost_time_injury") == "Yes" and rec.get("injury_status") == "No Injury":
        errs.append("A lost-time injury cannot have injury status 'No Injury'.")
    if not str(rec.get("corrective_action", "")).strip():
        errs.append("Corrective action is required (write 'Pending' if not yet decided).")
    return errs


def validate_equipment(rec, existing_ids=(), is_new=True):
    errs = []
    eid = str(rec.get("equipment_id", "")).strip().upper()
    if not re.fullmatch(r"[A-Z]{3}-\d{3}", eid):
        errs.append("Equipment ID must look like TRK-001.")
    elif is_new and eid in set(existing_ids):
        errs.append(f"Equipment ID {eid} already exists.")
    if rec.get("equipment_type") not in C.EQUIPMENT_TYPES:
        errs.append("Select a valid equipment type.")
    if not str(rec.get("manufacturer", "")).strip():
        errs.append("Manufacturer is required.")
    if to_number(rec.get("temperature"), -20, 250) is None:
        errs.append("Temperature must be a number between -20 and 250 deg C.")
    if to_number(rec.get("vibration"), 0, 100) is None:
        errs.append("Vibration must be a number between 0 and 100 mm/s.")
    for f in ("operating_hours", "fuel_consumption", "uptime_hours", "downtime_hours"):
        if to_number(rec.get(f), 0, 10_000_000) is None:
            errs.append(f"{f.replace('_', ' ').capitalize()} must be a number >= 0.")
    for f in ("brake_status", "tyre_status", "engine_status"):
        if rec.get(f) not in C.COMPONENT_STATUS:
            errs.append(f"Select a valid {f.replace('_', ' ')}.")
    if rec.get("maintenance_status") not in C.MAINTENANCE_STATUS:
        errs.append("Select a valid maintenance status.")
    return errs
