from rest_framework import serializers

from .models import Client, CaseFile, HearingSchedule


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'


class CaseFileSerializer(serializers.ModelSerializer):
    hearing_count = serializers.IntegerField(source='hearings.count', read_only=True)
    client_full_name = serializers.CharField(source='client.full_name', read_only=True)

    class Meta:
        model = CaseFile
        fields = '__all__'


class HearingScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = HearingSchedule
        fields = '__all__'
