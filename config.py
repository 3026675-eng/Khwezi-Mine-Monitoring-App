"""Central configuration: file paths, thresholds, roles and permissions.

IMPORTANT: all thresholds are EDUCATIONAL PROTOTYPE values only. They must not be
interpreted as manufacturer limits or statutory mine safety limits.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
FILES = {
    "users": DATA_DIR / "users.csv",
    "workers": DATA_DIR / "workers.csv",
    "incidents": DATA_DIR / "incidents.csv",
    "equipment": DATA_DIR / "equipment.csv",
}

# ---- Equipment condition thresholds (educational prototype values) ----
TEMP_WARNING, TEMP_CRITICAL = 80.0, 100.0      # deg C   (<80 normal, 80-100 warning, >100 critical)
VIB_WARNING, VIB_CRITICAL = 5.0, 8.0           # mm/s    (<5 normal, 5-8 warning, >8 critical)

# ---- Maintenance thresholds ----
LOW_AVAILABILITY = 80.0        # % availability below this is "low"
EXCESSIVE_DOWNTIME_H = 100.0   # downtime hours in the monitoring period
REPEATED_ALERTS = 3            # alerts in the last 30 days
DUE_SOON_DAYS = 14             # service due within this many days
PERIOD_HOURS = 720             # 30-day monitoring window used by the sample data

# ---- Worker safety thresholds ----
FATIGUE_WARNING, FATIGUE_CRITICAL = 7, 9   # fatigue scale 1-10
NEAR_MISS_LIMIT = 3
PREVIOUS_INCIDENT_LIMIT = 2
PPE_TARGET = 90.0              # department PPE compliance target (%)

# ---- Risk matrix: RiskScore = Likelihood x Consequence (1-5 each) ----
RISK_BANDS = [(1, 4, "Low"), (5, 9, "Medium"), (10, 16, "High"), (17, 25, "Critical")]

# ---- Domain lists ----
DEPARTMENTS = ["Underground Production", "Surface Mining", "Drilling & Blasting",
               "Processing Plant", "Engineering & Maintenance", "Hauling & Logistics"]
SHIFTS = ["Day", "Night"]
TRAINING_STATUS = ["Valid", "Expired", "Pending"]
SEVERITIES = ["Minor", "Moderate", "Major", "Critical"]
INJURY_STATUS = ["No Injury", "First Aid", "Medical Treatment", "Serious Injury"]
INCIDENT_STATUS = ["Open", "Under Investigation", "Closed"]
INCIDENT_TYPES = ["Slip/Trip/Fall", "Equipment-Related", "Fall of Ground", "Vehicle Collision",
                  "Struck by Object", "Fire/Explosion", "Electrical", "Chemical Exposure",
                  "Manual Handling", "Dust/Noise Exposure"]
CAUSES = ["Fatigue", "PPE not worn", "Equipment failure", "Inadequate supervision",
          "Procedure not followed", "Poor housekeeping", "Poor lighting/visibility",
          "Inadequate training", "Unsafe ground conditions"]
LOCATIONS = ["Pit North", "Pit South", "Shaft 1 - Level 12", "Shaft 2 - Level 8",
             "Processing Plant", "Workshop", "Crusher Station", "Haul Road"]
EQUIPMENT_TYPES = ["Haul Truck", "Loader", "Excavator", "Drilling Machine", "Bulldozer",
                   "Scraper Winch", "Crusher", "Conveyor"]
EQUIPMENT_PREFIX = {"Haul Truck": "TRK", "Loader": "LDR", "Excavator": "EXC",
                    "Drilling Machine": "DRL", "Bulldozer": "DOZ", "Scraper Winch": "SCW",
                    "Crusher": "CRU", "Conveyor": "CNV"}
COMPONENT_STATUS = ["OK", "Worn", "Fault", "N/A"]
MAINTENANCE_STATUS = ["Operational", "Under Maintenance", "Out of Service"]

# ---- Role-based access control (mirrors Table 1 of the brief) ----
ROLES = ["Administrator", "Safety Officer", "Mining Engineer", "Maintenance Engineer", "Manager"]
PERMISSIONS = {
    "dashboard":     {"Administrator", "Safety Officer", "Mining Engineer", "Maintenance Engineer", "Manager"},
    "worker_safety": {"Administrator", "Safety Officer", "Mining Engineer", "Manager"},
    "incidents":     {"Administrator", "Safety Officer", "Mining Engineer", "Manager"},
    "equipment":     {"Administrator", "Mining Engineer", "Maintenance Engineer", "Manager"},
    "maintenance":   {"Administrator", "Mining Engineer", "Maintenance Engineer", "Manager"},
    "risk":          {"Administrator", "Safety Officer", "Mining Engineer", "Manager"},
    "reports":       {"Administrator", "Safety Officer", "Mining Engineer", "Maintenance Engineer", "Manager"},
    "manage_users":  {"Administrator"},
}
# Alert category -> permission needed to see it
ALERT_PERMISSION = {"Equipment": "equipment", "Maintenance": "maintenance",
                    "Worker Safety": "worker_safety", "Incident": "incidents", "Risk": "risk"}
