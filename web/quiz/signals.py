"""Cohérence entre PostgreSQL et MongoDB à la suppression d'un compte.

Aucune clé étrangère ne relie les deux bases : quand un enseignant est
supprimé, ses leçons disparaissent en cascade dans PostgreSQL, et ce signal
supprime ses quiz dans MongoDB (pas de données orphelines, droit à
l'effacement du RGPD).
"""

from django.conf import settings
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .repository import QuizRepository


@receiver(post_delete, sender=settings.AUTH_USER_MODEL)
def supprimer_quiz_de_l_utilisateur(sender, instance, **kwargs):
    """Supprime les quiz MongoDB de l'utilisateur qui vient d'être supprimé."""
    QuizRepository().supprimer_par_utilisateur(instance.pk)
