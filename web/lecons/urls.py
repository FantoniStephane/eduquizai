from django.urls import path

from .views import LeconCreateView, LeconListView

app_name = "lecons"

urlpatterns = [
    path("", LeconListView.as_view(), name="liste"),
    path("nouvelle/", LeconCreateView.as_view(), name="creer"),
]
