from django.db import models


class Phone(models.Model):
    phone = models.CharField(max_length=20, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["phone", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"phone({self.phone})"

