import base64
import re
import uuid

from django.core.exceptions import ValidationError


PUBLIC_ID_PREFIX_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def make_public_id(prefix: str, record_id: uuid.UUID | str) -> str:
    """Build a stable human-readable ID from a semantic prefix and UUID.

    Public IDs intentionally derive from the UUID primary key instead of a random
    second identifier. That keeps generation deterministic, avoids coordination
    with future domain tables, and gives APIs a readable prefix such as
    ``lemma_`` or ``sense_`` without exposing sequential database IDs.
    """
    if not PUBLIC_ID_PREFIX_RE.fullmatch(prefix):
        raise ValidationError(
            "Public ID prefixes must be lowercase letters, numbers, or underscores "
            "and start with a letter."
        )

    uuid_value = (
        record_id if isinstance(record_id, uuid.UUID) else uuid.UUID(str(record_id))
    )
    public_suffix = (
        base64.b32encode(uuid_value.bytes).decode("ascii").rstrip("=").lower()
    )
    return f"{prefix}_{public_suffix}"
