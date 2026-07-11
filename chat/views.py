"""REST endpoints for the chat feature: inbox, history, starting a
conversation, a polling-fallback send, plus report and block."""
from django.utils.timezone import now
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chat.models import Conversation, Message
from chat.serializers import ConversationSerializer, MessageSerializer
from property.models import Property


def _conversations_for(user):
    return Conversation.objects.filter(
        is_deleted=False).filter(
        listing__owner=user).union(
        Conversation.objects.filter(is_deleted=False, initiator=user))


class ConversationListView(generics.ListAPIView):
    """The current user's inbox."""

    serializer_class = ConversationSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        ids = _conversations_for(user).values_list('id', flat=True)
        return Conversation.objects.filter(
            id__in=list(ids)).select_related(
            'listing', 'listing__owner', 'initiator').order_by('-updated_at')


class StartConversationView(APIView):
    """Start (or reopen) a conversation about a listing."""

    permission_classes = (IsAuthenticated,)

    def post(self, request, property_slug):
        listing = Property.active_objects.all_published().filter(
            slug=property_slug).first()
        if listing is None:
            return Response({'errors': 'we did not find the property'},
                            status=status.HTTP_404_NOT_FOUND)
        if listing.owner == request.user:
            return Response({
                'errors': 'you cannot start a chat about your own listing'},
                status=status.HTTP_400_BAD_REQUEST)
        conversation, _ = Conversation.objects.get_or_create(
            listing=listing, initiator=request.user)
        serializer = ConversationSerializer(
            conversation, context={'request': request})
        return Response({'data': {'conversation': serializer.data}},
                        status=status.HTTP_201_CREATED)


class MessageListCreateView(generics.ListCreateAPIView):
    """Paginated history plus a REST fallback for sending."""

    serializer_class = MessageSerializer
    permission_classes = (IsAuthenticated,)

    def _get_conversation(self):
        try:
            conversation = Conversation.objects.select_related(
                'listing').get(pk=self.kwargs['pk'], is_deleted=False)
        except Conversation.DoesNotExist:
            return None
        if not conversation.is_participant(self.request.user):
            return None
        return conversation

    def get_queryset(self):
        conversation = self._get_conversation()
        if conversation is None:
            return Message.objects.none()
        return conversation.messages.filter(is_deleted=False)

    def list(self, request, *args, **kwargs):
        if self._get_conversation() is None:
            return Response({'errors': 'conversation not found'},
                            status=status.HTTP_404_NOT_FOUND)
        # opening a thread marks it read
        Message.objects.filter(
            conversation_id=self.kwargs['pk'],
            read_at__isnull=True).exclude(sender=request.user).update(
            read_at=now())
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        conversation = self._get_conversation()
        if conversation is None:
            return Response({'errors': 'conversation not found'},
                            status=status.HTTP_404_NOT_FOUND)
        if conversation.is_blocked:
            return Response({
                'errors': 'this conversation has been blocked'},
                status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(sender=request.user, conversation=conversation)
        conversation.save(update_fields=['updated_at'])
        return Response({'data': {'message': serializer.data}},
                        status=status.HTTP_201_CREATED)


class ReportConversationView(APIView):
    """Flag a conversation for admin review."""

    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        try:
            conversation = Conversation.objects.select_related(
                'listing').get(pk=pk, is_deleted=False)
        except Conversation.DoesNotExist:
            return Response({'errors': 'conversation not found'},
                            status=status.HTTP_404_NOT_FOUND)
        if not conversation.is_participant(request.user):
            return Response({'errors': 'conversation not found'},
                            status=status.HTTP_404_NOT_FOUND)
        conversation.is_reported = True
        conversation.save(update_fields=['is_reported'])
        return Response({'message': 'Conversation reported. Our team '
                                    'will review it shortly.'})


class BlockConversationView(APIView):
    """Stop further messages in a conversation."""

    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        try:
            conversation = Conversation.objects.select_related(
                'listing').get(pk=pk, is_deleted=False)
        except Conversation.DoesNotExist:
            return Response({'errors': 'conversation not found'},
                            status=status.HTTP_404_NOT_FOUND)
        if not conversation.is_participant(request.user):
            return Response({'errors': 'conversation not found'},
                            status=status.HTTP_404_NOT_FOUND)
        conversation.is_blocked = True
        conversation.blocked_by = request.user
        conversation.save(update_fields=['is_blocked', 'blocked_by'])
        return Response({'message': 'Conversation blocked. The other '
                                    'party can no longer message you '
                                    'in this thread.'})
