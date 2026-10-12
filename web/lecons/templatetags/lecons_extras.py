"""Filtres de gabarit de l'application leçons."""

import re

from django import template
from django.utils.safestring import mark_safe

from ..conversion import markdown_vers_html

register = template.Library()


@register.filter
def markdown_sur(texte):
    """Affiche le Markdown d'une leçon en HTML nettoyé (protection XSS).

    La conversion et le nettoyage (liste blanche nh3) sont faits dans
    lecons/conversion.py : le résultat peut donc être marqué comme sûr.

    Les titres du contenu sont décalés d'un niveau (h3, h4…) : sur la page, ils
    sont placés sous la section « Contenu de la leçon » (h2), ce qui donne une
    hiérarchie de titres cohérente (accessibilité, RGAA critère 9.1).
    """
    html = re.sub(
        r"<(/?)h([2-5])>",
        lambda titre: f"<{titre[1]}h{int(titre[2]) + 1}>",
        markdown_vers_html(texte),
    )
    return mark_safe(html)  # sûr : HTML nettoyé par nh3, seuls les titres changent
