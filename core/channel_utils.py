"""Send new message to receiver's WebSocket group (call from sync message_create views)."""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .consumers import messages_group

logger = logging.getLogger(__name__)


def broadcast_new_message_to_receiver(receiver_id, message_data):
    """message_data: dict from MessageSerializer(msg).data."""
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.warning(
            "Channel layer is None; real-time message broadcast skipped. "
            "Set CHANNEL_LAYERS in settings and use Redis in production when using multiple processes."
        )
        return
    group = messages_group(receiver_id)
    async_to_sync(channel_layer.group_send)(
        group,
        {"type": "message.new", "message": message_data},
    )
