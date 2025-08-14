import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler

application = ProtocolTypeRouter({
    "http": ASGIStaticFilesHandler(
        get_asgi_application()
    ),
})
