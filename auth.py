"""Authentication and role-based access control (RBAC)."""
import hashlib
import hmac
import os

import pandas as pd

from . import config as C

ITERATIONS = 100_000
MAX_ATTEMPTS = 3


def hash_password(password, salt=None):
    salt = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS).hex()
    return salt, digest


def verify_password(password, salt, stored_hash):
    _, digest = hash_password(password, salt)
    return hmac.compare_digest(digest, stored_hash)


def load_users():
    return pd.read_csv(C.FILES["users"], dtype=str).fillna("")


def authenticate(username, password, users=None):
    """Return a user dict if credentials are valid and the account is active, else None."""
    if not username or not password:
        return None
    users = load_users() if users is None else users
    match = users[users["username"].str.lower() == username.strip().lower()]
    if match.empty:
        return None
    row = match.iloc[0]
    if row["active"].lower() != "yes":
        return None
    if verify_password(password, row["salt"], row["password_hash"]):
        return {"username": row["username"], "full_name": row["full_name"], "role": row["role"]}
    return None


def has_permission(role, function):
    return role in C.PERMISSIONS.get(function, set())


def allowed_functions(role):
    return [f for f, roles in C.PERMISSIONS.items() if role in roles]


def _strong(password):
    return len(password) >= 8 and not password.isalpha() and not password.isdigit()


def add_user(username, full_name, role, password):
    """Add a user; returns (ok, message)."""
    users = load_users()
    username = username.strip()
    if not username.isalnum() or len(username) < 3:
        return False, "Username must be at least 3 letters/numbers (no spaces or symbols)."
    if (users["username"].str.lower() == username.lower()).any():
        return False, "That username already exists."
    if role not in C.ROLES:
        return False, "Invalid role."
    if not _strong(password):
        return False, "Password needs 8+ characters mixing letters and numbers."
    salt, digest = hash_password(password)
    users.loc[len(users)] = [username, full_name.strip() or username, role, salt, digest, "Yes"]
    users.to_csv(C.FILES["users"], index=False)
    return True, f"User '{username}' created with role {role}."


def set_active(username, active):
    users = load_users()
    users.loc[users["username"] == username, "active"] = "Yes" if active else "No"
    users.to_csv(C.FILES["users"], index=False)


def reset_password(username, new_password):
    if not _strong(new_password):
        return False, "Password needs 8+ characters mixing letters and numbers."
    users = load_users()
    salt, digest = hash_password(new_password)
    users.loc[users["username"] == username, ["salt", "password_hash"]] = [salt, digest]
    users.to_csv(C.FILES["users"], index=False)
    return True, "Password updated."
