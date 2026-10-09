"""Adresses de l'application quiz."""

from django.urls import path

from .views import QuizGenerationView, QuizListView, annuler_generation

app_name = "quiz"

urlpatterns = [
    path("", QuizListView.as_view(), name="liste"),
    path("generer/", QuizGenerationView.as_view(), name="generer"),
    path("generer/annuler/", annuler_generation, name="annuler_generation"),
]
