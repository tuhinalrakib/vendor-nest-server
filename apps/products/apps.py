from django.apps import AppConfig
import threading

class ProductsConfig(AppConfig):
    name = 'products'

    def ready(self):
        from . import signals  # noqa
        
        # Automatically run migrations in a background thread to prevent startup block
        def run_migrations_bg():
            from django.core.management import call_command
            import time
            
            # Wait a few seconds for Django to initialize fully
            time.sleep(2)
            try:
                print("[SaaS Startup] Running automated database migrations...")
                call_command('makemigrations', 'products', interactive=False)
                call_command('migrate', interactive=False)
                print("[SaaS Startup] Automated migrations completed successfully!")
            except Exception as e:
                print("[SaaS Startup] Migration failed or already completed:", e)

        threading.Thread(target=run_migrations_bg, daemon=True).start()
