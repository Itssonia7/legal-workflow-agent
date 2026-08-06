from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        LAWYER = 'lawyer', 'Lawyer'
        ADMIN = 'admin', 'Admin'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.LAWYER,
    )
    phone = models.CharField(max_length=20, blank=True, default='')

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'
