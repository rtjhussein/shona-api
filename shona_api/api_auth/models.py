import secrets
from dataclasses import dataclass

from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone


@dataclass(frozen=True)
class ParsedAPIKey:
    prefix: str
    raw_key: str


class APIKeyManager(models.Manager):
    def create_key(self, *, name, plan, rate_limit_per_minute=None):
        prefix = self._make_unique_prefix()
        raw_key = f"shona_sk_{prefix}_{secrets.token_urlsafe(32)}"
        api_key = self.create(
            name=name,
            prefix=prefix,
            key_hash=make_password(raw_key),
            plan=plan,
            rate_limit_per_minute=(
                rate_limit_per_minute
                if rate_limit_per_minute is not None
                else APIKey.default_rate_limit_for_plan(plan)
            ),
        )
        return api_key, raw_key

    def get_from_raw_key(self, raw_key):
        parsed_key = APIKey.parse_raw_key(raw_key)
        if parsed_key is None:
            return None

        try:
            api_key = self.get(prefix=parsed_key.prefix, is_active=True)
        except self.model.DoesNotExist:
            return None

        if not api_key.verify(parsed_key.raw_key):
            return None
        return api_key

    def _make_unique_prefix(self):
        while True:
            prefix = secrets.token_urlsafe(9).replace("-", "").replace("_", "")[:12]
            if not self.filter(prefix=prefix).exists():
                return prefix


class APIKey(models.Model):
    class Plan(models.TextChoices):
        DEVELOPER = "developer", "Developer"
        STANDARD = "standard", "Standard"
        PARTNER = "partner", "Partner"

    PLAN_RATE_LIMITS = {
        Plan.DEVELOPER: 60,
        Plan.STANDARD: 600,
        Plan.PARTNER: 3000,
    }

    name = models.CharField(max_length=120)
    prefix = models.CharField(
        max_length=24,
        unique=True,
        db_index=True,
        help_text="Non-secret key prefix used for lookup and support.",
    )
    key_hash = models.CharField(max_length=255)
    plan = models.CharField(
        max_length=32,
        choices=Plan.choices,
        default=Plan.DEVELOPER,
        db_index=True,
    )
    rate_limit_per_minute = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True, db_index=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = APIKeyManager()

    class Meta:
        ordering = ("name",)
        indexes = [
            models.Index(fields=("plan", "is_active")),
        ]

    @property
    def is_authenticated(self):
        return True

    def __str__(self):
        return f"{self.name} ({self.prefix})"

    @classmethod
    def default_rate_limit_for_plan(cls, plan):
        return cls.PLAN_RATE_LIMITS[plan]

    @classmethod
    def parse_raw_key(cls, raw_key):
        if not raw_key or not raw_key.startswith("shona_sk_"):
            return None

        parts = raw_key.split("_", 3)
        if len(parts) != 4 or parts[0] != "shona" or parts[1] != "sk":
            return None
        return ParsedAPIKey(prefix=parts[2], raw_key=raw_key)

    def verify(self, raw_key):
        return check_password(raw_key, self.key_hash)

    def mark_used(self, when=None):
        self.last_used_at = when or timezone.now()
        self.save(update_fields=("last_used_at", "updated_at"))

    def revoke(self, when=None):
        self.is_active = False
        self.revoked_at = when or timezone.now()
        self.save(update_fields=("is_active", "revoked_at", "updated_at"))
