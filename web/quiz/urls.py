"""Adresses de l'application quiz."""

from django.urls import path

from .views import (
    QuizDetailView,
    QuizGenerationView,
    QuizListView,
    QuizModificationView,
    QuizSuppressionView,
    annuler_generation,
    valider_un_quiz,
)

app_name = "quiz"

urlpatterns = [
    path("", QuizListView.as_view(), name="liste"),
    path("generer/", QuizGenerationView.as_view(), name="generer"),
    path("generer/annuler/", annuler_generation, name="annuler_generation"),
    path("<str:id_quiz>/", QuizDetailView.as_view(), name="detail"),
    path("<str:id_quiz>/valider/", valider_un_quiz, name="valider"),
    path("<str:id_quiz>/modifier/", QuizModificationView.as_view(), name="modifier"),
    path("<str:id_quiz>/supprimer/", QuizSuppressionView.as_view(), name="supprimer"),
]
