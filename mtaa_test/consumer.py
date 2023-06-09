# chat/consumers.py
import base64
import json
from mtaa_test.models import Account, Room, Message
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.files.base import ContentFile


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.group_name = "chat_%s" % self.room_id

        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.group_name, self.channel_name
        )

        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name, self.channel_name
        )

    def receive(self, text_data=None, bytes_data=None):
        text_data_json = json.loads(text_data)
        message_type = text_data_json["type"]
        message_content = text_data_json["message"]
        sender_id = text_data_json["sender_id"]
        room_id = text_data_json["room_id"]

        account_instance = Account.objects.get(id=sender_id)
        room_instance = Room.objects.get(id=room_id)
        message_instance = None

        if message_type == 'chat_message':
            message_instance = Message(text=message_content, account=account_instance, room=room_instance)
            message_instance.save()

        elif message_type == 'image_message':
            image_data = text_data_json["image"]

            if "base64" in image_data:
                image_base64 = image_data["base64"]
                image_type = image_data["type"]
                image_name = image_data["name"]
                decoded_image = base64.b64decode(image_base64)
                print("Received base64 image:", image_base64)

                # Save the image
                image_file = ContentFile(decoded_image, name=image_name)
                message_instance = Message(text=message_content, account=account_instance, room=room_instance,
                                           image=image_file)
                message_instance.save()
            else:
                print("Error: 'base64' key is missing in image_data:", image_data)

        msg = {
            "text": message_content,
            "account": sender_id,
            "room": room_id,
            "image_url": message_instance.image.url if message_instance.image else None,
            "image_base64": text_data_json["image"]["base64"] if message_instance.image else None,
            "image_type": text_data_json["image"]["type"] if message_instance.image else None,
        }

        channel_layer = get_channel_layer()
        async_to_sync(self.channel_layer.group_send)(
            self.group_name, {"type": "chat_message", "message": msg}
        )

    def chat_message(self, event):
        msg = event["message"]
        print(msg)
        self.send(text_data=json.dumps(msg))