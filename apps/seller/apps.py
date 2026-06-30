from django.apps import AppConfig


class SellerConfig(AppConfig):
    name = 'seller'

    def ready(self):
        from . import signals

