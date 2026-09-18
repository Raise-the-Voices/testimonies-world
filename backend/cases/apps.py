from django.apps import AppConfig


class CasesConfig(AppConfig):
    name = 'cases'

    def ready(self):
        # Import the signal handlers so @receiver decorators attach.
        # Imported inside ready() so the AppConfig loads early and
        # signals register once Django's app registry is built.
        from . import signals  # noqa: F401  (imported for side effects)
