from rest_framework import viewsets, permissions
from .models import Client, CaseFile, HearingSchedule, LegalDocument
from .serializers import (
    ClientSerializer,
    CaseFileSerializer,
    HearingScheduleSerializer,
    LegalDocumentSerializer
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

class LegalDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = LegalDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return LegalDocument.objects.all()
        return LegalDocument.objects.filter(case_file__lawyer=self.request.user).order_by('-uploaded_at')
