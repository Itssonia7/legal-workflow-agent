import json
from rest_framework import viewsets, views, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from django.shortcuts import get_object_or_404
from django.http import StreamingHttpResponse, HttpResponse
from cases.models import CaseFile
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer

from ai_engine.chat_engine import (
    retrieve_chat_context_private,
    retrieve_chat_context_public,
    generate_chat_stream,
    redact_pii
)

class PublicChatThrottle(AnonRateThrottle):
    rate = '20/minute'


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'role', '') == 'admin':
            return Conversation.objects.all().order_by('-updated_at')
        return Conversation.objects.filter(user=user).order_by('-updated_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SendMessageStreamView(views.APIView):
    """
    POST /api/chat/conversations/{id}/send/
    Authenticated endpoint streaming SSE events for AI response.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk=None, *args, **kwargs):
        user = request.user
        if getattr(user, 'role', '') == 'admin':
            conversation = get_object_or_404(Conversation, id=pk)
        else:
            conversation = get_object_or_404(Conversation, id=pk, user=user)

        query = request.data.get('query', '').strip()
        if not query:
            return Response({"error": "Field 'query' is required."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Update title automatically if it's default
        if conversation.title in ["New Legal Consultation", "New Chat", ""]:
            first_line = query.split('\n')[0][:50].strip()
            conversation.title = first_line if first_line else "Legal Consultation"
            conversation.save(update_fields=['title'])

        # 2. Save User message to DB (redacted)
        user_msg = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content=redact_pii(query)
        )

        # 3. Retrieve prior history from DB
        history_msgs = list(
            Message.objects.filter(conversation=conversation)
            .exclude(id=user_msg.id)
            .order_by('created_at')
        )
        history_data = [{"role": m.role, "content": m.content} for m in history_msgs]

        # 4. Compute allowed case IDs for user
        if getattr(user, 'role', '') == 'admin':
            allowed_case_ids = list(CaseFile.objects.values_list('id', flat=True))
        else:
            allowed_case_ids = list(CaseFile.objects.filter(lawyer=user).values_list('id', flat=True))

        selected_case_id = conversation.case_file.id if conversation.case_file else None

        # 5. Retrieve Context with distance threshold
        context_chunks, sources, is_grounded = retrieve_chat_context_private(
            allowed_case_ids=allowed_case_ids,
            query=query,
            selected_case_id=selected_case_id
        )

        # 6. Stream generator wrapper that saves Assistant message on completion or disconnect
        def stream_generator():
            accumulated_assistant_text = ""
            final_sources = sources
            final_grounded = is_grounded

            try:
                for event_chunk in generate_chat_stream(
                    query=query,
                    history=history_data,
                    context_chunks=context_chunks,
                    is_grounded=is_grounded,
                    is_public=False
                ):
                    # Parse event to accumulate assistant text
                    if event_chunk.startswith("data: "):
                        try:
                            payload = json.loads(event_chunk[6:].strip())
                            if "token" in payload:
                                accumulated_assistant_text += payload["token"]
                            if payload.get("done"):
                                if "full_text" in payload:
                                    accumulated_assistant_text = payload["full_text"]
                                final_grounded = payload.get("grounded", is_grounded)
                        except Exception:
                            pass

                    yield event_chunk

            finally:
                # Save Assistant message to DB (even if disconnected or partial)
                if accumulated_assistant_text.strip():
                    cleaned_content = redact_pii(accumulated_assistant_text.strip())
                    Message.objects.create(
                        conversation=conversation,
                        role=Message.Role.ASSISTANT,
                        content=cleaned_content,
                        sources=final_sources,
                        grounded=final_grounded
                    )
                    conversation.save(update_fields=['updated_at'])

        response = StreamingHttpResponse(stream_generator(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response


class PublicChatView(views.APIView):
    """
    POST /api/chat/public/
    Stateless public endpoint. Strictly restricted to statutes.
    authentication_classes = [] prevents 401 on stale Bearer tokens.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [PublicChatThrottle]

    def post(self, request, *args, **kwargs):
        query = request.data.get('query', '').strip()
        if not query:
            return Response({"error": "Field 'query' is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Enforce max length (1000 chars)
        if len(query) > 1000:
            return Response({"error": "Query exceeds max length of 1000 characters."}, status=status.HTTP_400_BAD_REQUEST)

        # History turns cap (max last 6 turns)
        history_raw = request.data.get('history', [])
        if not isinstance(history_raw, list):
            history_raw = []
        history_capped = history_raw[-6:]

        # Server-side STRICT statute-only retrieval
        context_chunks, sources, is_grounded = retrieve_chat_context_public(query=query)

        def stream_generator():
            for event_chunk in generate_chat_stream(
                query=query,
                history=history_capped,
                context_chunks=context_chunks,
                is_grounded=is_grounded,
                is_public=True
            ):
                yield event_chunk

        response = StreamingHttpResponse(stream_generator(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
