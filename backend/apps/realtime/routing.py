from django.urls import path

from .consumers import WorkspaceConsumer

websocket_urlpatterns = [path("ws/workspace/", WorkspaceConsumer.as_asgi())]
