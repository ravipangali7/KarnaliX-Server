"""
Support-related serializers for KarnaliX.
"""
from rest_framework import serializers
from core.models import SupportTicket, SupportMessage


class SupportMessageSerializer(serializers.ModelSerializer):
    """Serializer for support messages."""
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    sender_role = serializers.CharField(source='sender.role', read_only=True)
    
    class Meta:
        model = SupportMessage
        fields = ['id', 'ticket', 'sender', 'sender_username', 'sender_role', 'message', 'attachment_url', 'created_at']


class SupportMessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating support messages."""
    class Meta:
        model = SupportMessage
        fields = ['message', 'attachment_url']


class SupportTicketSerializer(serializers.ModelSerializer):
    """Serializer for support tickets."""
    username = serializers.CharField(source='user.username', read_only=True)
    assigned_to_username = serializers.CharField(source='assigned_to.username', read_only=True, allow_null=True)
    messages = SupportMessageSerializer(many=True, read_only=True)
    messages_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SupportTicket
        fields = [
            'id', 'user', 'username', 'subject', 'category', 'priority',
            'status', 'assigned_to', 'assigned_to_username',
            'messages', 'messages_count', 'created_at', 'updated_at'
        ]
    
    def get_messages_count(self, obj):
        return obj.messages.count()


class SupportTicketListSerializer(serializers.ModelSerializer):
    """Serializer for support ticket list (without messages)."""
    username = serializers.CharField(source='user.username', read_only=True)
    assigned_to_username = serializers.CharField(source='assigned_to.username', read_only=True, allow_null=True)
    messages_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SupportTicket
        fields = [
            'id', 'user', 'username', 'subject', 'category', 'priority',
            'status', 'assigned_to', 'assigned_to_username',
            'messages_count', 'created_at', 'updated_at'
        ]
    
    def get_messages_count(self, obj):
        return obj.messages.count()


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating support tickets."""
    initial_message = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = SupportTicket
        fields = ['subject', 'category', 'priority', 'initial_message']


class SupportTicketUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating support tickets."""
    class Meta:
        model = SupportTicket
        fields = ['status', 'priority', 'assigned_to']
