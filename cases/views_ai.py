import os
from rest_framework import views, status, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.conf import settings

from .models import CaseFile, LegalDocument
from .serializers import LegalDocumentSerializer

# Import AI Engine components
from ai_engine.ingest import process_legal_document
from ai_engine.graph import app as ai_app

class DocumentUploadAndIngestView(views.APIView):
    """
    POST /api/cases/documents/upload/
    Uploads a legal PDF document, saves it to the database,
    and runs the local ChromaDB ingestion pipeline.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        case_id = request.data.get('case_file')
        file_obj = request.FILES.get('file')

        if not case_id or not file_obj:
            return Response(
                {"error": "Both 'case_file' ID and 'file' are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        case_file = get_object_or_404(CaseFile, id=case_id, lawyer=request.user)

        # Create LegalDocument record
        doc = LegalDocument.objects.create(
            case_file=case_file,
            file=file_obj,
            name=file_obj.name,
            indexed=False
        )

        # Ingest file content into ChromaDB
        file_path = doc.file.path
        if os.path.exists(file_path):
            try:
                print(f"[Backend] Triggering ChromaDB ingestion for: {file_path}")
                process_legal_document(file_path, case_id)
                doc.indexed = True
                doc.save()
            except Exception as e:
                doc.delete()  # Clean up if ingestion fails
                return Response(
                    {"error": f"Failed to ingest document: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        serializer = LegalDocumentSerializer(doc)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class AIDraftGeneratorView(views.APIView):
    """
    POST /api/cases/draft/
    Triggers the LangGraph multi-agent loop to generate a Critic-approved legal draft.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user_prompt = request.data.get('user_prompt')
        case_id = request.data.get('case_file')

        if not user_prompt:
            return Response(
                {"error": "Field 'user_prompt' is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        case_file = get_object_or_404(CaseFile, id=case_id, lawyer=request.user) if case_id else None

        print(f"[Backend] Starting LangGraph multi-agent system with prompt: {user_prompt} for Case ID: {case_id}")

        initial_state = {
            "user_prompt": user_prompt,
            "case_id": str(case_file.id) if case_file else "",
            "context_documents": "",
            "current_draft": "",
            "critic_feedback": "",
            "revision_count": 0,
            "is_approved": False,
            "step_logs": []
        }

        try:
            # Execute the LangGraph loop (limit depth to 20 steps to allow enough drafting cycles)
            result = ai_app.invoke(initial_state, config={"recursion_limit": 20})
            
            return Response({
                "user_prompt": result.get("user_prompt"),
                "context_documents": result.get("context_documents"),
                "current_draft": result.get("current_draft"),
                "is_approved": result.get("is_approved"),
                "revision_count": result.get("revision_count"),
                "critic_feedback": result.get("critic_feedback"),
                "step_logs": result.get("step_logs", [])
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"LangGraph execution failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
