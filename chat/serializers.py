from rest_framework import serializers
from cases.models import CaseFile
from .models import Conversation, Message

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'

class ConversationSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    case_file_title = serializers.ReadOnlyField(source='case_file.title')
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ('id', 'user', 'title', 'case_file', 'case_file_title', 'messages', 'created_at', 'updated_at')

    def validate_case_file(self, value):
        if value is None:
            return value

        request = self.context.get('request')
        if not request or not request.user:
            return value

        user = request.user
        if getattr(user, 'role', '') == 'admin':
            return value

        # Check ownership for standard lawyers
        if value.lawyer != user:
            raise serializers.ValidationError("Selected case file does not belong to your account.")
            
        return value
