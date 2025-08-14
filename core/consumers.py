from channels.generic.websocket import AsyncWebsocketConsumer
from django.template.loader import render_to_string
from .models import Message, Conversation
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
import json

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        user = self.scope["user"]
        text_data_json = json.loads(text_data)
        message_text = text_data_json['message']

        message = await self.save_message(user, message_text)

        message_html = await self.render_message_to_html(message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "html": message_html
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({"html": event["html"]}))

    @sync_to_async
    def save_message(self, user, message_text):
        conversation, _ = Conversation.objects.get_or_create(room_name=self.room_name)
        return Message.objects.create(
            conversation=conversation,
            sender=user,
            text=message_text
        )

    @sync_to_async
    def render_message_to_html(self, message):
        return render_to_string("chat/message.html", {"message": message})