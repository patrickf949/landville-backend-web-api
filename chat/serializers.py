import re

from rest_framework import serializers

from chat.models import Conversation, Message

TAG_RE = re.compile(r'<[^>]+>')


class MessageSerializer(serializers.ModelSerializer):
    """Serialize a plain-text chat message. Anything that looks like
    markup is stripped so the chat stays strictly text-based."""

    sender = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ('id', 'conversation', 'sender', 'body', 'read_at',
                  'created_at')
        read_only_fields = ('id', 'conversation', 'sender', 'read_at',
                            'created_at')

    def get_sender(self, obj):
        return {
            'id': obj.sender.pk,
            'email': obj.sender.email,
            'first_name': obj.sender.first_name,
            'last_name': obj.sender.last_name,
        }

    def validate_body(self, body):
        body = TAG_RE.sub('', str(body)).strip()
        if not body:
            raise serializers.ValidationError(
                'Message cannot be empty.')
        if len(body) > Message.MAX_LENGTH:
            raise serializers.ValidationError(
                f'Messages cannot be longer than {Message.MAX_LENGTH} '
                f'characters.')
        return body


class ConversationSerializer(serializers.ModelSerializer):
    """Inbox representation of a conversation."""

    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    listing = serializers.SerializerMethodField()
    other_party = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ('id', 'listing', 'other_party', 'last_message',
                  'unread_count', 'is_blocked', 'updated_at')

    def get_listing(self, obj):
        return {
            'slug': obj.listing.slug,
            'title': obj.listing.title,
            'image_main': obj.listing.image_main,
            'listing_type': obj.listing.get_listing_type_display().title(),
            'price': float(obj.listing.price),
        }

    def get_other_party(self, obj):
        me = self.context['request'].user
        other = obj.listing.owner if obj.initiator == me else obj.initiator
        return {
            'id': other.pk,
            'email': other.email,
            'first_name': other.first_name,
            'last_name': other.last_name,
        }

    def get_last_message(self, obj):
        last = obj.messages.filter(is_deleted=False).last()
        return MessageSerializer(last).data if last else None

    def get_unread_count(self, obj):
        me = self.context['request'].user
        return obj.messages.filter(
            is_deleted=False, read_at__isnull=True).exclude(
            sender=me).count()
