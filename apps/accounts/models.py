from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        DEVELOPER = "developer", "Developer"
        REVIEWER = "reviewer", "Reviewer"
        ADMINISTRATOR = "administrator", "Administrator"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.DEVELOPER)

    def __str__(self) -> str:
        return self.get_username()

# Create your models here.
