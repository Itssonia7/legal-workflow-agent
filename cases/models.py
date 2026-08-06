from django.conf import settings
from django.db import models


class Client(models.Model):
    client_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=255)
    contact_info = models.CharField(max_length=255, blank=True)
    email = models.EmailField()
    lawyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='clients',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.full_name} (Client #{self.client_id})'


class CaseFile(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        CLOSED = 'closed', 'Closed'
        PENDING = 'pending', 'Pending'

    case_id = models.AutoField(primary_key=True)
    case_title = models.CharField(max_length=255)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OPEN,
    )
    case_type = models.CharField(max_length=255)
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='cases',
    )
    lawyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cases',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.case_title} [{self.get_status_display()}]'


class HearingSchedule(models.Model):
    schedule_id = models.AutoField(primary_key=True)
    hearing_date = models.DateTimeField()
    description = models.TextField(blank=True)
    case = models.ForeignKey(
        CaseFile,
        on_delete=models.CASCADE,
        related_name='hearings',
    )
    reminder_sent = models.BooleanField(default=False)

    def __str__(self):
        return f'Hearing on {self.hearing_date} — {self.case.case_title}'
