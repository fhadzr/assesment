"""Role model (task 2.x / design D4)."""

CALLER_ROLES = ("hr", "finance", "exec")
PERMISSION_ALL = "all"
VALID_ROLE_TOKENS = frozenset({"all", "hr", "finance", "exec"})


def allowed(doc: dict, role: str) -> bool:
    """Access predicate: a doc is visible if the role is in allowed_roles, or the
    doc declares the 'all' permission (visible to every caller role)."""
    return role in doc["allowed_roles"] or PERMISSION_ALL in doc["allowed_roles"]
