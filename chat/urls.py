from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet, SendMessageStreamView, PublicChatView

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')

urlpatterns = [
    path('public/', PublicChatView.as_view(), name='chat-public'),
    path('conversations/<int:pk>/send/', SendMessageStreamView.as_view(), name='chat-send-stream'),
    path('', include(router.urls)),
]
