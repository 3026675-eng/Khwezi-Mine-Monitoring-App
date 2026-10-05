"""Risk assessment: RiskScore = Likelihood x Consequence (1-5 scale)."""
import pandas as pd

from . import config as C


def risk_score(likelihood, consequence):
    for v in (likelihood, consequence):
        if not isinstance(v, (int, float)) or int(v) != v or not 1 <= v <= 5:
            raise ValueError("Likelihood and consequence must be whole numbers from 1 to 5.")
    return int(likelihood) * int(consequence)


def classify_risk(score):
    for low, high, label in C.RISK_BANDS:
        if low <= score <= high:
            return label
    raise ValueError(f"Risk score {score} is outside the 1-25 range.")


def risk_warning(level):
    if level == "Critical":
        return "CRITICAL RISK: stop work in the affected area and escalate to management immediately."
    if level == "High":
        return "HIGH RISK: implement additional controls and notify the safety officer."
    return ""


def assess(likelihood, consequence):
    score = risk_score(likelihood, consequence)
    level = classify_risk(score)
    return {"score": score, "level": level, "warning": risk_warning(level)}


def risk_matrix():
    """5x5 matrix of scores (rows = likelihood 5..1, columns = consequence 1..5)."""
    data = {f"Consequence {c}": [l * c for l in range(5, 0, -1)] for c in range(1, 6)}
    return pd.DataFrame(data, index=[f"Likelihood {l}" for l in range(5, 0, -1)])
