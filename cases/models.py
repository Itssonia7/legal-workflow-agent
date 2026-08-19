from django.db import models
from django.conf import settings

class Client(models.Model):
    lawyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='clients')
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    address = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class CaseFile(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        CLOSED = 'closed', 'Closed'
        PENDING = 'pending', 'Pending'

    lawyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cases')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='cases')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OPEN
    )
    citation_tags = models.TextField(blank=True, default='', help_text="Keywords or references associated with the case")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.client.name}"

class HearingSchedule(models.Model):
    case_file = models.ForeignKey(CaseFile, on_delete=models.CASCADE, related_name='hearings')
    hearing_date = models.DateTimeField()
    description = models.TextField(blank=True, default='')
    court_room = models.CharField(max_length=50, blank=True, default='')
    collision_warning = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.case_file.title} on {self.hearing_date}"

class LegalDocument(models.Model):
    case_file = models.ForeignKey(CaseFile, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to='legal_documents/')
    name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    indexed = models.BooleanField(default=False)

    def __str__(self):
        return self.name

# Signals to trigger Celery tasks
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=HearingSchedule)
def trigger_collision_check(sender, instance, **kwargs):
    from .tasks import check_hearing_schedule_collision
    check_hearing_schedule_collision.delay(instance.id)
