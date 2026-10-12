from django.urls import path

from .views import (
    LeconCreateView,
    LeconDeleteView,
    LeconDetailView,
    LeconListView,
    LeconUpdateView,
    importer_un_texte,
)

app_name = "lecons"

urlpatterns = [
    path("", LeconListView.as_view(), name="liste"),
    path("nouvelle/", LeconCreateView.as_view(), name="creer"),
    path("importer/", importer_un_texte, name="importer"),
    path("<int:pk>/", LeconDetailView.as_view(), name="detail"),
    path("<int:pk>/modifier/", LeconUpdateView.as_view(), name="modifier"),
    path("<int:pk>/supprimer/", LeconDeleteView.as_view(), name="supprimer"),
]
