"""Adresses de l'application quiz."""

from django.urls import path

from .views import QuizListView

app_name = "quiz"

urlpatterns = [
    path("", QuizListView.as_view(), name="liste"),
]
