from django.urls import path
from complaint.views import (
    api_create_complaint, api_list_complaints,
    api_list_chat_messages, api_send_chat_message
)

app_name = "complaint"

urlpatterns = [
    path("create/", api_create_complaint, name="api_create_complaint"),
    path("list/", api_list_complaints, name="api_list_complaints"),
    path("chat/list/", api_list_chat_messages, name="api_list_chat_messages"),
    path("chat/send/", api_send_chat_message, name="api_send_chat_message"),
]
