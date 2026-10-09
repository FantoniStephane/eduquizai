"""Adresses du microservice IA : une seule API, sous /api/."""

from django.urls import include, path

urlpatterns = [
    path("api/", include("generation.urls")),
]
