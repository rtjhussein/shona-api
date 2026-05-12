from django.db import models


class EditorialRole(models.TextChoices):
    VIEWER = "viewer", "Viewer"
    EDITOR = "editor", "Editor"
    ADMIN = "admin", "Admin"


VIEWER_PERMISSIONS = frozenset(
    {
        "editorial.view_reviewnote",
        "editorial.view_editorialdecision",
        "editorial.view_editorialdecisionrecord",
        "editorial.view_auditlog",
    }
)

EDITOR_PERMISSIONS = VIEWER_PERMISSIONS | frozenset(
    {
        "editorial.add_reviewnote",
        "editorial.change_reviewnote",
        "editorial.add_editorialdecision",
        "editorial.change_editorialdecision",
        "editorial.add_editorialdecisionrecord",
        "editorial.change_editorialdecisionrecord",
        "editorial.add_auditlog",
    }
)

ADMIN_PERMISSIONS = EDITOR_PERMISSIONS | frozenset(
    {
        "editorial.delete_reviewnote",
        "editorial.delete_editorialdecision",
        "editorial.delete_editorialdecisionrecord",
        "editorial.change_auditlog",
        "editorial.delete_auditlog",
    }
)

EDITORIAL_ROLE_PERMISSIONS = {
    EditorialRole.VIEWER: VIEWER_PERMISSIONS,
    EditorialRole.EDITOR: EDITOR_PERMISSIONS,
    EditorialRole.ADMIN: ADMIN_PERMISSIONS,
}


def user_has_editorial_permission(user, permission):
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user.has_perm(permission)
