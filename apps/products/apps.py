from django.apps import AppConfig
import threading

class ProductsConfig(AppConfig):
    name = 'products'

    def ready(self):
        from . import signals  # noqa

