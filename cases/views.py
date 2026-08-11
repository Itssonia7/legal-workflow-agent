from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from .models import Client, CaseFile, HearingSchedule
from .serializers import ClientSerializer, CaseFileSerializer, HearingScheduleSerializer


class ClientViewSet(ModelViewSet):
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Client.objects.all()
        return Client.objects.filter(lawyer=user)


class CaseFileViewSet(ModelViewSet):
    serializer_class = CaseFileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return CaseFile.objects.all()
        return CaseFile.objects.filter(lawyer=user)


class HearingScheduleViewSet(ModelViewSet):
    serializer_class = HearingScheduleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return HearingSchedule.objects.all()
        return HearingSchedule.objects.filter(case__lawyer=user)
