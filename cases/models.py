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
    content_hash = models.CharField(max_length=64, blank=True, default='', db_index=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    indexed = models.BooleanField(default=False)

    def __str__(self):
        return self.name

# Signals to trigger Celery tasks
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=HearingSchedule)
def trigger_collision_check(sender, instance, **kwargs):
    from .tasks import check_hearing_schedule_collision
    check_hearing_schedule_collision.delay(instance.id)

@receiver(post_delete, sender=LegalDocument)
def purge_document_vectors(sender, instance, **kwargs):
    """
    Purge vectors from ChromaDB and clean up physical file from storage when a LegalDocument is deleted.
    """
    import os
    import chromadb
    # 1. Purge vectors from ChromaDB
    try:
        db_path = os.path.join(settings.BASE_DIR, "ai_engine", "chroma_db")
        client = chromadb.PersistentClient(path=db_path)
        collection = client.get_collection("legal_knowledge_vault")
        collection.delete(where={"document_id": str(instance.id)})
        print(f"[ChromaDB] Purged vectors for document ID: {instance.id}")
    except Exception as e:
        print(f"Error purging document vectors for document {instance.id}: {e}")

    # 2. Delete physical file if no other document references its content hash
    if instance.content_hash:
        duplicates = LegalDocument.objects.filter(content_hash=instance.content_hash).exclude(id=instance.id)
        if not duplicates.exists():
            if instance.file and os.path.exists(instance.file.path):
                try:
                    os.remove(instance.file.path)
                    print(f"[Storage] Deleted physical file: {instance.file.path}")
                except Exception as e:
                    print(f"Error deleting physical file {instance.file.path}: {e}")
