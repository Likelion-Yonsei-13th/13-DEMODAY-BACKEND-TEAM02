from django.apps import AppConfig


class ChatappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ChatApp"

    def ready(self):
        from . import signals  # noqa: F401
