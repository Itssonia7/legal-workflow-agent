import os
import shutil
import tempfile
from unittest.mock import patch, MagicMock
from django.test import override_settings
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from accounts.models import User
from cases.models import Client, CaseFile, LegalDocument

# Use a temporary directory for MEDIA_ROOT to avoid polluting the workspace
TEMP_MEDIA_ROOT = tempfile.mkdtemp()

@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class LegalDocumentDeduplicationTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        # Initialize test API Client
        self.api_client = APIClient()

        # Create a test lawyer user
        self.user = User.objects.create_user(
            username='testlawyer',
            password='password123',
            role='lawyer'
        )
        self.api_client.force_authenticate(user=self.user)

        # Create Client and Case Files
        self.client_obj = Client.objects.create(lawyer=self.user, name='John Doe')
        self.case_a = CaseFile.objects.create(lawyer=self.user, client=self.client_obj, title='Case A')
        self.case_b = CaseFile.objects.create(lawyer=self.user, client=self.client_obj, title='Case B')

        # Dummy PDF file content
        self.pdf_content = b"%PDF-1.4 ... dummy pdf content representing a legal document ..."
        self.uploaded_file = SimpleUploadedFile(
            name="agreement.pdf",
            content=self.pdf_content,
            content_type="application/pdf"
        )

    @patch('chromadb.PersistentClient')
    @patch('cases.views_ai.process_legal_document')
    def test_upload_lifecycle_deduplication_and_cleanup(self, mock_process, mock_chroma):
        """
        Verify the full lifecycle:
        1. First upload works and creates file/vectors.
        2. Second identical upload in the same case is blocked (409 Conflict).
        3. Third identical upload in a different case reuses the file path but creates new vectors.
        4. Deleting the first upload keeps the file on disk (reference count = 1).
        5. Deleting the second upload removes the file from disk (reference count = 0).
        """
        # Mock ChromaDB Collection
        mock_collection = MagicMock()
        mock_client = MagicMock()
        mock_client.get_collection.return_value = mock_collection
        mock_chroma.return_value = mock_client

        # ----------------------------------------------------
        # Step 1: Upload a unique file to Case A
        # ----------------------------------------------------
        response_1 = self.api_client.post(
            '/api/cases/documents/upload/',
            {'case_file': self.case_a.id, 'file': self.uploaded_file},
            format='multipart'
        )
        self.assertEqual(response_1.status_code, status.HTTP_201_CREATED)
        doc_1 = LegalDocument.objects.get(id=response_1.data['id'])
        
        self.assertTrue(doc_1.indexed)
        self.assertIsNotNone(doc_1.content_hash)
        self.assertTrue(os.path.exists(doc_1.file.path))
        
        # Verify ingest pipeline was called for doc_1
        mock_process.assert_called_once_with(doc_1.file.path, str(self.case_a.id), doc_1.id)
        mock_process.reset_mock()

        # ----------------------------------------------------
        # Step 2: Upload the same file again to Case A (Same-Case Duplicate)
        # ----------------------------------------------------
        # Reset the file stream pointer so it can be read again
        self.uploaded_file.seek(0)
        response_2 = self.api_client.post(
            '/api/cases/documents/upload/',
            {'case_file': self.case_a.id, 'file': self.uploaded_file},
            format='multipart'
        )
        self.assertEqual(response_2.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("already been uploaded", response_2.data['error'])
        mock_process.assert_not_called()

        # ----------------------------------------------------
        # Step 3: Upload the same file to Case B (Cross-Case Sharing)
        # ----------------------------------------------------
        self.uploaded_file.seek(0)
        response_3 = self.api_client.post(
            '/api/cases/documents/upload/',
            {'case_file': self.case_b.id, 'file': self.uploaded_file},
            format='multipart'
        )
        self.assertEqual(response_3.status_code, status.HTTP_201_CREATED)
        doc_3 = LegalDocument.objects.get(id=response_3.data['id'])

        # Verify that both database records point to the exact same file path (Deduplication)
        self.assertEqual(doc_1.file.name, doc_3.file.name)
        self.assertEqual(doc_1.content_hash, doc_3.content_hash)

        # Ingestion should still be called for Case B to index chunks under the new case scope
        mock_process.assert_called_once_with(doc_3.file.path, str(self.case_b.id), doc_3.id)
        mock_process.reset_mock()

        # ----------------------------------------------------
        # Step 4: Delete doc_1 from Case A (File should stay, vectors deleted)
        # ----------------------------------------------------
        doc_1_id = doc_1.id
        doc_1_file_path = doc_1.file.path
        
        doc_1.delete()

        # Verify vectors were purged for doc_1
        mock_collection.delete.assert_any_call(where={"document_id": str(doc_1_id)})
        
        # Physical file should STILL exist because Case B (doc_3) still references it
        self.assertTrue(os.path.exists(doc_1_file_path))

        # ----------------------------------------------------
        # Step 5: Delete doc_3 from Case B (File and vectors should be fully deleted)
        # ----------------------------------------------------
        doc_3_id = doc_3.id
        mock_collection.reset_mock()
        
        doc_3.delete()

        # Verify vectors were purged for doc_3
        mock_collection.delete.assert_any_call(where={"document_id": str(doc_3_id)})

        # Physical file should now be deleted since the reference count reached 0
        self.assertFalse(os.path.exists(doc_1_file_path))
