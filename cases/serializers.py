from rest_framework import serializers
from .models import Client, CaseFile, HearingSchedule, LegalDocument, DraftHistory

class ClientSerializer(serializers.ModelSerializer):
    lawyer = serializers.ReadOnlyField(source='lawyer.username')

    class Meta:
        model = Client
        fields = '__all__'

class CaseFileSerializer(serializers.ModelSerializer):
    lawyer = serializers.ReadOnlyField(source='lawyer.username')
    client_name = serializers.ReadOnlyField(source='client.name')

    class Meta:
        model = CaseFile
        fields = '__all__'

class HearingScheduleSerializer(serializers.ModelSerializer):
    case_title = serializers.ReadOnlyField(source='case_file.title')

    class Meta:
        model = HearingSchedule
        fields = '__all__'

class LegalDocumentSerializer(serializers.ModelSerializer):
    case_title = serializers.ReadOnlyField(source='case_file.title')

    class Meta:
        model = LegalDocument
        fields = '__all__'

class DraftHistorySerializer(serializers.ModelSerializer):
    case_title = serializers.ReadOnlyField(source='case_file.title')
    lawyer_username = serializers.ReadOnlyField(source='lawyer.username')

    class Meta:
        model = DraftHistory
        fields = [
            'id', 'lawyer', 'lawyer_username', 'case_file', 'case_title',
            'prompt', 'draft_text', 'is_approved', 'revision_count', 'created_at'
        ]
        read_only_fields = fields
