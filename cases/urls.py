from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClientViewSet,
    CaseFileViewSet,
    HearingScheduleViewSet,
    LegalDocumentViewSet
)

router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'cases', CaseFileViewSet, basename='case')
router.register(r'schedules', HearingScheduleViewSet, basename='schedule')
router.register(r'documents', LegalDocumentViewSet, basename='document')

from .views_ai import DocumentUploadAndIngestView, AIDraftGeneratorView

urlpatterns = [
    path('documents/upload/', DocumentUploadAndIngestView.as_view(), name='document-upload'), # Match specific path first!
    path('', include(router.urls)),
    path('draft/', AIDraftGeneratorView.as_view(), name='ai-draft'),
]
