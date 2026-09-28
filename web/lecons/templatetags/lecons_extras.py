"""Filtres de gabarit de l'application leçons."""

from django import template
from django.utils.safestring import mark_safe

from ..conversion import markdown_vers_html

register = template.Library()


@register.filter
def markdown_sur(texte):
    """Affiche le Markdown d'une leçon en HTML nettoyé (protection XSS).

    La conversion et le nettoyage (liste blanche nh3) sont faits dans
    lecons/conversion.py : le résultat peut donc être marqué comme sûr.
    """
    return mark_safe(markdown_vers_html(texte))  # sûr : HTML nettoyé par nh3
