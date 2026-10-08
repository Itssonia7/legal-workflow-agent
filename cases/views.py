from rest_framework import viewsets, permissions
from .models import Client, CaseFile, HearingSchedule, LegalDocument, DraftHistory
from .serializers import (
    ClientSerializer,
    CaseFileSerializer,
    HearingScheduleSerializer,
    LegalDocumentSerializer,
    DraftHistorySerializer
)

class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return Client.objects.all()
        return Client.objects.filter(lawyer=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(lawyer=self.request.user)

class CaseFileViewSet(viewsets.ModelViewSet):
    serializer_class = CaseFileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return CaseFile.objects.all()
        return CaseFile.objects.filter(lawyer=self.request.user).order_by('-updated_at')

    def perform_create(self, serializer):
        serializer.save(lawyer=self.request.user)

class HearingScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = HearingScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return HearingSchedule.objects.all()
        return HearingSchedule.objects.filter(case_file__lawyer=self.request.user).order_by('hearing_date')

from ai_engine.ingest import delete_document_vectors

class LegalDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = LegalDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return LegalDocument.objects.all()
        return LegalDocument.objects.filter(case_file__lawyer=self.request.user).order_by('-uploaded_at')

    def perform_destroy(self, instance):
        doc_id = instance.id
        # 1. Clean up vectors from ChromaDB
        try:
            delete_document_vectors(doc_id)
        except Exception as e:
            print(f"Warning: Failed to delete ChromaDB vectors for document {doc_id}: {e}")
            
        # 2. Clean up media file from disk
        if instance.file:
            instance.file.delete(save=False)
            
        # 3. Delete database record
        instance.delete()

class DraftHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DraftHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return DraftHistory.objects.all().order_by('-created_at')
        return DraftHistory.objects.filter(lawyer=self.request.user).order_by('-created_at')
