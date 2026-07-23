from django.urls import path

from chat.views import (
    BlockConversationView, ConversationListView, MessageListCreateView,
    ReportConversationView, StartConversationView)

urlpatterns = [
    path('conversations/', ConversationListView.as_view(),
         name='chat_inbox'),
    path('conversations/start/<slug:property_slug>/',
         StartConversationView.as_view(), name='chat_start'),
    path('conversations/<int:pk>/messages/',
         MessageListCreateView.as_view(), name='chat_messages'),
    path('conversations/<int:pk>/report/',
         ReportConversationView.as_view(), name='chat_report'),
    path('conversations/<int:pk>/block/',
         BlockConversationView.as_view(), name='chat_block'),
]
