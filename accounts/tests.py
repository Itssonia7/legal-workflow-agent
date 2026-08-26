from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.username = 'akash'
        self.password = 'StrongPass123!'
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email='akash@example.com',
            role=User.Role.LAWYER
        )

    def test_login_returns_user_object(self):
        response = self.client.post('/api/auth/login/', {
            'username': self.username,
            'password': self.password
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'akash')
        self.assertEqual(response.data['user']['id'], self.user.id)

