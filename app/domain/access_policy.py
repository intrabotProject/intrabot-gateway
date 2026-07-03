"""
Politique d'accès documentaire : rôles utilisateur ↔ catégories de documents.

Chaque document indexé possède une catégorie. Chaque utilisateur possède un rôle.
Le gateway filtre documents et recherches selon la matrice ROLE_CATEGORIES.

Matrice rôle → catégories
-------------------------
employee   → public
engineer   → public, engineering
manager    → public, engineering, gouvernance
rh         → public, rh
admin      → toutes (public, engineering, rh, gouvernance, finance)

Exposition API : GET /api/v1/access (sans authentification).
Application  : GatewayService.search, list_documents_for_role, user_routes.submit_document.
"""

from typing import Literal

DocumentCategory = Literal["public", "engineering", "rh", "gouvernance", "finance"]
UserRole = Literal["employee", "engineer", "manager", "rh", "admin"]

DOCUMENT_CATEGORIES: tuple[DocumentCategory, ...] = (
    "public",
    "engineering",
    "rh",
    "gouvernance",
    "finance",
)

USER_ROLES: tuple[UserRole, ...] = (
    "employee",
    "engineer",
    "manager",
    "rh",
    "admin",
)

REGISTERABLE_ROLES: tuple[UserRole, ...] = (
    "employee",
    "engineer",
    "manager",
    "rh",
)

DEFAULT_USER_ROLE: UserRole = "employee"

CATEGORY_LABELS: dict[DocumentCategory, str] = {
    "public": "Public (tous)",
    "engineering": "Technique / Ingénierie",
    "rh": "Ressources humaines",
    "gouvernance": "Gouvernance",
    "finance": "Finance",
}

ROLE_LABELS: dict[UserRole, str] = {
    "employee": "Collaborateur",
    "engineer": "Ingénieur logiciel",
    "manager": "Manager",
    "rh": "Ressources humaines",
    "admin": "Administrateur",
}

ROLE_CATEGORIES: dict[UserRole, tuple[DocumentCategory, ...]] = {
    "employee": ("public",),
    "engineer": ("public", "engineering"),
    "manager": ("public", "engineering", "gouvernance"),
    "rh": ("public", "rh"),
    "admin": DOCUMENT_CATEGORIES,
}


def normalize_user_role(raw: str) -> UserRole:
    """Valide et normalise un rôle utilisateur (minuscules, liste USER_ROLES)."""
    normalized = raw.strip().lower()
    if normalized not in USER_ROLES:
        raise ValueError(
            f"Invalid role '{raw}'. Allowed: {', '.join(USER_ROLES)}"
        )
    return normalized  # type: ignore[return-value]


def get_allowed_categories(role: UserRole) -> list[str]:
    """Retourne les catégories documentaires accessibles pour un rôle donné."""
    return list(ROLE_CATEGORIES[role])
