import os
import shutil
import tempfile
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

from cases.models import Client, CaseFile
from chat.models import Conversation, Message
from ai_engine.chat_engine import (
    retrieve_chat_context_private,
    retrieve_chat_context_public,
    COSINE_DISTANCE_THRESHOLD
)

User = get_user_model()

class ChatBackendTests(TestCase):
    def setUp(self):
        self.api_client = APIClient()

        # Create User A (Lawyer A)
        self.user_a = User.objects.create_user(
            username='lawyer_a',
            password='password123',
            role='lawyer'
        )
        self.client_a = Client.objects.create(lawyer=self.user_a, name='Client A')
        self.case_a = CaseFile.objects.create(lawyer=self.user_a, client=self.client_a, title='Case A')

        # Create User B (Lawyer B)
        self.user_b = User.objects.create_user(
            username='lawyer_b',
            password='password123',
            role='lawyer'
        )
        self.client_b = Client.objects.create(lawyer=self.user_b, name='Client B')
        self.case_b = CaseFile.objects.create(lawyer=self.user_b, client=self.client_b, title='Case B')

    # 1. Validation Test: User A cannot attach User B's case file
    def test_cannot_attach_other_user_case_file(self):
        self.api_client.force_authenticate(user=self.user_a)

        # Attempt to create conversation referencing User B's case_file
        response = self.api_client.post('/api/chat/conversations/', {
            'title': 'Intruder Consultation',
            'case_file': self.case_b.id
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('case_file', response.data)

        # Valid create with User A's case_file
        valid_res = self.api_client.post('/api/chat/conversations/', {
            'title': 'Valid Consultation',
            'case_file': self.case_a.id
        }, format='json')
        self.assertEqual(valid_res.status_code, status.HTTP_201_CREATED)
        conv_id = valid_res.data['id']

        # Attempt PATCH to switch to User B's case_file
        patch_res = self.api_client.patch(f'/api/chat/conversations/{conv_id}/', {
            'case_file': self.case_b.id
        }, format='json')
        self.assertEqual(patch_res.status_code, status.HTTP_400_BAD_REQUEST)

    # 2. Owner Isolation: User A cannot view User B's conversations
    def test_conversation_owner_isolation(self):
        conv_b = Conversation.objects.create(user=self.user_b, title='Secret B Chat')

        self.api_client.force_authenticate(user=self.user_a)
        res = self.api_client.get(f'/api/chat/conversations/{conv_b.id}/')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        list_res = self.api_client.get('/api/chat/conversations/')
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_res.data), 0)

    # 3. Public Endpoint Isolation & No Auth Error on Stale Headers
    @patch('ai_engine.chat_engine.get_chroma_collection')
    def test_public_endpoint_isolation(self, mock_chroma):
        mock_coll = MagicMock()
        mock_coll.query.return_value = {
            "documents": [["Section 29 Aadhaar Act statute content"]],
            "distances": [[0.5]],
            "metadatas": [[{"act_name": "Aadhaar Act", "section_no": "Section 29"}]]
        }
        mock_chroma.return_value = mock_coll

        client = APIClient()
        # Even with stale/bad Authorization header, public view should proceed (auth_classes = [])
        client.credentials(HTTP_AUTHORIZATION='Bearer stale_invalid_token')

        res = client.post('/api/chat/public/', {
            'query': 'What is Section 29?',
            'case_file': self.case_a.id  # Intentionally pass case_file field
        }, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        # Verify chroma query was called STRICTLY with source_type="statute"
        mock_coll.query.assert_called_once_with(
            query_texts=['What is Section 29?'],
            n_results=5,
            where={"source_type": "statute"}
        )

    # 4. Private Retrieval Isolation in Chroma Engine
    @patch('ai_engine.chat_engine.get_chroma_collection')
    def test_private_retrieval_case_isolation(self, mock_chroma):
        mock_coll = MagicMock()
        
        def mock_query(query_texts, n_results, where=None):
            if where and where.get("source_type") == "statute":
                return {"documents": [[]], "distances": [[]], "metadatas": [[]]}
            return {
                "documents": [["User A case file content"]],
                "distances": [[0.4]],
                "metadatas": [[{"source_type": "case_file", "source_file": "doc_a.pdf", "case_id": str(self.case_a.id)}]]
            }

        mock_coll.query.side_effect = mock_query
        mock_chroma.return_value = mock_coll

        # Query private context for User A (allowed case IDs = [self.case_a.id])
        allowed_case_ids = [self.case_a.id]
        chunks, sources, grounded = retrieve_chat_context_private(
            allowed_case_ids=allowed_case_ids,
            query="Aadhaar breach facts"
        )

        self.assertTrue(grounded)
        self.assertEqual(len(chunks), 1)
        
        # Verify where clause in query targeted only case_a.id
        mock_coll.query.assert_any_call(
            query_texts=["Aadhaar breach facts"],
            n_results=4,
            where={"$and": [{"source_type": "case_file"}, {"case_id": str(self.case_a.id)}]}
        )

    # 5. Fallback Notice Verification when no chunks pass threshold
    @patch('ai_engine.chat_engine.get_chroma_collection')
    def test_fallback_notice_when_unsupported(self, mock_chroma):
        mock_coll = MagicMock()
        # Return distance 1.8 (above 1.15 threshold)
        mock_coll.query.return_value = {
            "documents": [["Irrelevant document"]],
            "distances": [[1.8]],
            "metadatas": [[{"source_type": "statute", "act_name": "Unrelated"}]]
        }
        mock_chroma.return_value = mock_coll

        chunks, sources, grounded = retrieve_chat_context_public("How to make chocolate cake?")
        self.assertFalse(grounded)
        self.assertEqual(len(chunks), 0)

    # 6. Public Throttling Test
    def test_public_rate_limiting(self):
        client = APIClient()
        # Send requests until throttled
        for i in range(25):
            res = client.post('/api/chat/public/', {'query': 'hello'}, format='json')
            if res.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                break
        
        self.assertEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
