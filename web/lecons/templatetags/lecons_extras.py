"""Filtres de gabarit de l'application leçons."""

import markdown
import nh3
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Balises gardées après conversion : la mise en forme d'une leçon, rien d'autre.
# Pas de h1 (réservé au titre de la page), pas de script, d'image ni de style.
BALISES_AUTORISEES = {
    "p", "br", "h2", "h3", "h4", "ul", "ol", "li",
    "strong", "em", "blockquote", "code", "pre", "hr", "a",
}  # fmt: skip
ATTRIBUTS_AUTORISES = {"a": {"href"}}


@register.filter
def markdown_sur(texte):
    """Convertit le Markdown d'une leçon en HTML nettoyé (protection XSS).

    Le HTML produit par Markdown est filtré par nh3 : seules les balises de
    mise en forme sont conservées, les liens ne peuvent viser que http, https
    ou mailto, et reçoivent rel="noopener noreferrer".
    """
    html = markdown.markdown(texte or "", extensions=["nl2br", "sane_lists"])
    propre = nh3.clean(
        html,
        tags=BALISES_AUTORISEES,
        attributes=ATTRIBUTS_AUTORISES,
        url_schemes={"http", "https", "mailto"},
    )
    return mark_safe(propre)  # sûr : le HTML vient d'être nettoyé par nh3
