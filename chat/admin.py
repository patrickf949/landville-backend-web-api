from django.contrib import admin

from chat.models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'listing', 'initiator', 'is_blocked',
                    'is_reported', 'updated_at')
    list_filter = ('is_blocked', 'is_reported')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'created_at', 'read_at')
