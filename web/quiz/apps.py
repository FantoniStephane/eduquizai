from django.apps import AppConfig


class QuizConfig(AppConfig):
    """Configuration de l'application « quiz » (quiz stockés dans MongoDB)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "quiz"
