"""Conversions du contenu d'une leçon : le Markdown est le format de référence.

Quel que soit le mode de saisie (éditeur Trix, zone de texte, import), le contenu
est enregistré en Markdown : c'est ce texte que l'IA reçoit pour générer un quiz.
Tout HTML est nettoyé par nh3 (liste blanche) avant d'être converti ou affiché.
"""

import re

import markdown
import nh3
from markdownify import MarkdownConverter

# Balises de mise en forme autorisées : rien d'autre ne passe (ni script, ni
# image, ni style). Les liens ne peuvent viser que http, https ou mailto.
BALISES_AUTORISEES = {
    "p", "div", "br", "h1", "h2", "h3", "h4", "ul", "ol", "li",
    "strong", "b", "em", "i", "blockquote", "code", "pre", "hr", "a",
}  # fmt: skip
ATTRIBUTS_AUTORISES = {"a": {"href"}}
SCHEMAS_AUTORISES = {"http", "https", "mailto"}


def nettoyer_html(html):
    """Ne garde que les balises de mise en forme autorisées (protection XSS)."""
    return nh3.clean(
        html or "",
        tags=BALISES_AUTORISEES,
        attributes=ATTRIBUTS_AUTORISES,
        url_schemes=SCHEMAS_AUTORISES,
    )


class _ConvertisseurLecon(MarkdownConverter):
    """Convertisseur HTML vers Markdown : les titres deviennent des « ## »."""

    def convert_h1(self, el, text, *args, **kwargs):
        """Le titre de l'éditeur (h1) devient un titre de section « ## »."""
        return f"\n\n## {text.strip()}\n\n"

    convert_h2 = convert_h1


def html_vers_markdown(html):
    """Convertit le HTML de l'éditeur en Markdown, après nettoyage.

    Args:
        html: contenu envoyé par le formulaire.

    Returns:
        Le Markdown à enregistrer en base.
    """
    propre = nettoyer_html(html).replace("\xa0", " ").replace("&nbsp;", " ")
    texte = _ConvertisseurLecon(heading_style="ATX", bullets="-").convert(propre)
    texte = re.sub(r"\n{3,}", "\n\n", texte)
    return texte.strip()


def markdown_vers_html(texte):
    """Convertit le Markdown enregistré en HTML nettoyé (affichage de la leçon).

    Un « # titre » devient un h2 : le h1 de la page est réservé au titre de la leçon.
    """
    html = markdown.markdown(texte or "", extensions=["nl2br", "sane_lists"])
    html = re.sub(r"<(/?)h1>", r"<\1h2>", html)
    return nettoyer_html(html)


def markdown_vers_html_editeur(texte):
    """HTML à charger dans l'éditeur Trix, qui ne connaît qu'un niveau de titre."""
    html = markdown_vers_html(texte)
    # Les retours à la ligne entre blocs deviendraient des lignes vides dans Trix ;
    # les espaces entre deux mots mis en forme (sans retour à la ligne) sont gardés.
    html = re.sub(r">\s*\n\s*<", "><", html)
    return re.sub(r"<(/?)h[2-4]>", r"<\1h1>", html)
