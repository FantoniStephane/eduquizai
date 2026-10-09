"""Adresses de l'API de génération."""

from django.urls import path

from .views import GenererQuizView

urlpatterns = [
    path("generer-quiz/", GenererQuizView.as_view(), name="generer-quiz"),
]
