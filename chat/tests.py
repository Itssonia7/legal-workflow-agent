import os
import shutil
import tempfile
import chromadb
from chromadb.utils import embedding_functions
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
    generate_chat_stream,
    DISTANCE_THRESHOLD,
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

        # Create Admin User
        self.admin_user = User.objects.create_user(
            username='admin_user',
            password='password123',
            role='admin'
        )

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

    # 2. Admin Role Bypass Test (role == 'admin')
    def test_admin_role_can_attach_any_case_file(self):
        self.api_client.force_authenticate(user=self.admin_user)

        # Admin can attach User B's case_file without ownership error
        response = self.api_client.post('/api/chat/conversations/', {
            'title': 'Admin Oversight Consultation',
            'case_file': self.case_b.id
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['case_file'], self.case_b.id)

    # 3. Owner Isolation: User A cannot view User B's conversations
    def test_conversation_owner_isolation(self):
        conv_b = Conversation.objects.create(user=self.user_b, title='Secret B Chat')

        self.api_client.force_authenticate(user=self.user_a)
        res = self.api_client.get(f'/api/chat/conversations/{conv_b.id}/')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        list_res = self.api_client.get('/api/chat/conversations/')
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_res.data), 0)

    # 4. Real Chroma Vector Retrieval Isolation Test
    def test_real_chroma_user_isolation(self):
        # Create in-memory EphemeralClient for isolated vector testing
        client = chromadb.Client()
        embedding_func = embedding_functions.DefaultEmbeddingFunction()
        coll = client.create_collection(
            name="test_isolation_vault",
            embedding_function=embedding_func,
            metadata={"hnsw:space": "cosine"}
        )

        # Ingest real vector chunks for User A's case and User B's case
        coll.add(
            ids=["chunk_a1", "chunk_b1"],
            documents=[
                "User A confidential agreement terms regarding solar property lease",
                "User B confidential agreement terms regarding solar property lease"
            ],
            metadatas=[
                {"source_type": "case_file", "source_file": "user_a_contract.pdf", "case_id": "101"},
                {"source_type": "case_file", "source_file": "user_b_contract.pdf", "case_id": "202"}
            ]
        )

        with patch('ai_engine.chat_engine.get_chroma_collection', return_value=coll):
            # User A has allowed_case_ids = [101]
            chunks_a, sources_a, grounded_a = retrieve_chat_context_private(
                allowed_case_ids=[101],
                query="solar property lease"
            )
            
            # Assert User A ONLY retrieves Chunk A (case_id 101) and NEVER Chunk B (case_id 202)
            self.assertTrue(grounded_a)
            self.assertEqual(len(chunks_a), 1)
            self.assertEqual(chunks_a[0]['case_id'], "101")
            self.assertEqual(chunks_a[0]['source_file'], "user_a_contract.pdf")

            # User B has allowed_case_ids = [202]
            chunks_b, sources_b, grounded_b = retrieve_chat_context_private(
                allowed_case_ids=[202],
                query="solar property lease"
            )

            # Assert User B ONLY retrieves Chunk B (case_id 202) and NEVER Chunk A (case_id 101)
            self.assertTrue(grounded_b)
            self.assertEqual(len(chunks_b), 1)
            self.assertEqual(chunks_b[0]['case_id'], "202")
            self.assertEqual(chunks_b[0]['source_file'], "user_b_contract.pdf")

    # 5. Public Endpoint Isolation & No Auth Error on Stale Headers
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

    # 6. Fallback Notice Exact Wording Verification
    @patch('ai_engine.chat_engine.check_ollama_health', return_value=True)
    @patch('ai_engine.chat_engine.ChatOllama')
    def test_fallback_notice_exact_wording(self, mock_ollama_class, mock_health):
        mock_llm = MagicMock()
        mock_llm.stream.return_value = []
        mock_ollama_class.return_value = mock_llm

        # Test Private Fallback
        private_gen = generate_chat_stream(
            query="Chocolate cake recipe",
            history=[],
            context_chunks=[],
            is_grounded=False,
            is_public=False
        )
        first_private_event = next(private_gen)
        self.assertIn("I didn't find this in your database, so I'm answering based on general knowledge.", first_private_event)

        # Test Public Fallback
        public_gen = generate_chat_stream(
            query="Chocolate cake recipe",
            history=[],
            context_chunks=[],
            is_grounded=False,
            is_public=True
        )
        first_public_event = next(public_gen)
        self.assertIn("I didn't find this in the public legal database, so I'm answering based on general knowledge.", first_public_event)

    # 7. Public Rate Limiting Test
    @override_settings(PUBLIC_CHAT_THROTTLE_RATE='5/hour')
    def test_public_rate_limiting(self):
        client = APIClient()
        for i in range(6):
            res = client.post('/api/chat/public/', {'query': 'hello'}, format='json')
            if res.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                break
        
        self.assertEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    # 8. Metric-Aware Threshold Test
    def test_metric_aware_threshold(self):
        from ai_engine.chat_engine import get_effective_distance_threshold

        coll_l2 = MagicMock()
        coll_l2.metadata = {"hnsw:space": "l2"}
        self.assertEqual(get_effective_distance_threshold(coll_l2), 1.15)

        coll_none = MagicMock()
        coll_none.metadata = None
        self.assertEqual(get_effective_distance_threshold(coll_none), 1.15)

        coll_cosine = MagicMock()
        coll_cosine.metadata = {"hnsw:space": "cosine"}
        self.assertEqual(get_effective_distance_threshold(coll_cosine), 0.575)

