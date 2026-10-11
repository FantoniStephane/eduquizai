"""Export d'un quiz en PDF, version élève (tâche 40).

Seule la version élève est exportée : le corrigé (bonnes réponses,
explications, réponse attendue) reste dans l'espace de l'enseignant. La
fonction qui dessine le PDF ne reçoit que le résultat de ``version_eleve`` :
les réponses ne peuvent donc pas se retrouver dans le fichier, même par
erreur. Le PDF utilise la police Helvetica intégrée aux lecteurs PDF (aucun
fichier de police embarqué, fichier plus léger).
"""

from io import BytesIO
from xml.sax.saxutils import escape

from django.utils.text import slugify
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

LIGNES_REPONSE = 4
"""Nombre de lignes laissées pour répondre à une question ouverte."""

CONSIGNE = (
    "Pour les QCM et les Vrai / Faux, cochez la bonne réponse. "
    "Pour les questions ouvertes, répondez sur les lignes."
)

_ENCRE = HexColor("#1f2937")
_GRIS = HexColor("#6b7280")
_MARGE = 18 * mm

_STYLES = {
    "titre": ParagraphStyle(
        "titre", fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=_ENCRE
    ),
    "sous_titre": ParagraphStyle(
        "sous_titre", fontName="Helvetica", fontSize=10, leading=13, textColor=_GRIS
    ),
    "consigne": ParagraphStyle(
        "consigne", fontName="Helvetica-Oblique", fontSize=10, leading=13
    ),
    "question": ParagraphStyle(
        "question", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=_ENCRE
    ),
    "choix": ParagraphStyle("choix", fontName="Helvetica", fontSize=11, leading=14),
    "identite": ParagraphStyle(
        "identite", fontName="Helvetica", fontSize=10, leading=13
    ),
}


def version_eleve(quiz):
    """Ne garde du quiz que ce que l'élève doit voir.

    Args:
        quiz: quiz lu dans MongoDB (dictionnaire du repository).

    Returns:
        dict: ``titre`` et ``questions`` ; chaque question n'a que ``numero``,
        ``type_question``, ``texte`` et ``choix`` (liste de libellés). Aucune
        bonne réponse, explication ni réponse attendue.
    """
    questions = sorted(quiz["questions"], key=lambda question: question["ordre"])
    return {
        "titre": quiz["titre"],
        "questions": [
            {
                "numero": numero,
                "type_question": question["type_question"],
                "texte": question["texte"],
                "choix": [choix["texte"] for choix in question["choix"]],
            }
            for numero, question in enumerate(questions, start=1)
        ],
    }


def nom_fichier(quiz):
    """Nom du fichier téléchargé, tiré du titre (ex. ``quiz-les-volcans.pdf``).

    Args:
        quiz: quiz lu dans MongoDB.

    Returns:
        str: nom sans accent ni caractère spécial.
    """
    return f"quiz-{slugify(quiz['titre'])[:80] or 'eleve'}.pdf"


def _texte(valeur):
    """Échappe un texte pour ReportLab, qui lit une forme de balisage XML.

    Sans cela, un « < » écrit par l'IA ou l'enseignant casserait le PDF ou
    serait interprété comme une balise.
    """
    return escape(valeur).replace("\n", "<br/>")


class _Choix(Flowable):
    """Une case à cocher suivie du libellé du choix."""

    COTE = 3.4 * mm
    RETRAIT = 8 * mm

    def __init__(self, libelle):
        super().__init__()
        self.paragraphe = Paragraph(_texte(libelle), _STYLES["choix"])

    def wrap(self, largeur, hauteur):
        """Calcule la place occupée par le libellé (retour à la ligne compris)."""
        _, hauteur_texte = self.paragraphe.wrap(largeur - self.RETRAIT, hauteur)
        self.width, self.height = largeur, hauteur_texte
        return self.width, self.height

    def draw(self):
        """Dessine la case alignée sur la première ligne, puis le libellé."""
        haut = self.height - _STYLES["choix"].leading
        self.canv.setStrokeColor(_ENCRE)
        self.canv.rect(2 * mm, haut + 0.8 * mm, self.COTE, self.COTE)
        self.paragraphe.drawOn(self.canv, self.RETRAIT, 0)


class _Lignes(Flowable):
    """Lignes pointillées pour écrire la réponse à une question ouverte."""

    ECART = 8 * mm

    def __init__(self, nombre):
        super().__init__()
        self.nombre = nombre

    def wrap(self, largeur, hauteur):
        """Une hauteur fixe par ligne."""
        self.width, self.height = largeur, self.nombre * self.ECART
        return self.width, self.height

    def draw(self):
        """Dessine les lignes de bas en haut."""
        self.canv.setStrokeColor(_GRIS)
        self.canv.setDash(1, 2)
        for rang in range(self.nombre):
            y = rang * self.ECART + 1 * mm
            self.canv.line(0, y, self.width, y)


def _identite():
    """Cadre « Nom / Prénom / Classe / Date » à remplir par l'élève."""
    cellules = [
        Paragraph(f"{libelle} : ", _STYLES["identite"])
        for libelle in ("Nom", "Prénom", "Classe", "Date")
    ]
    tableau = Table(
        [cellules[:2], cellules[2:]],
        colWidths="50%",
        rowHeights=9 * mm,
    )
    tableau.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, _ENCRE),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, _GRIS),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return tableau


def _question(question):
    """Bloc d'une question, gardé sur une même page."""
    elements = [
        Paragraph(
            f"{question['numero']}. {_texte(question['texte'])}", _STYLES["question"]
        ),
        Spacer(1, 2 * mm),
    ]
    if question["type_question"] == "ouverte":
        elements.append(_Lignes(LIGNES_REPONSE))
    else:
        for libelle in question["choix"]:
            elements += [_Choix(libelle), Spacer(1, 1.5 * mm)]
    elements.append(Spacer(1, 6 * mm))
    return KeepTogether(elements)


def _pied_de_page(canvas, document):
    """Numéro de page en bas, centré."""
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(_GRIS)
    canvas.drawCentredString(A4[0] / 2, 10 * mm, f"Page {document.page}")
    canvas.restoreState()


def generer_pdf_eleve(quiz, matiere="", niveau=""):
    """Produit le PDF à distribuer aux élèves.

    Args:
        quiz: quiz lu dans MongoDB ; seule sa version élève est utilisée.
        matiere: matière de la leçon d'origine (libellé affiché).
        niveau: niveau scolaire de la leçon d'origine (libellé affiché).

    Returns:
        bytes: contenu du fichier PDF (A4).
    """
    eleve = version_eleve(quiz)
    tampon = BytesIO()
    document = SimpleDocTemplate(
        tampon,
        pagesize=A4,
        leftMargin=_MARGE,
        rightMargin=_MARGE,
        topMargin=_MARGE,
        bottomMargin=_MARGE,
        title=eleve["titre"],
        author="",
        creator="EduQuizAI",
    )
    elements = [Paragraph(_texte(eleve["titre"]), _STYLES["titre"])]
    precisions = " · ".join(valeur for valeur in (matiere, niveau) if valeur)
    if precisions:
        elements += [
            Spacer(1, 1 * mm),
            Paragraph(_texte(precisions), _STYLES["sous_titre"]),
        ]
    elements += [
        Spacer(1, 5 * mm),
        _identite(),
        Spacer(1, 5 * mm),
        Paragraph(CONSIGNE, _STYLES["consigne"]),
        Spacer(1, 6 * mm),
    ]
    elements += [_question(question) for question in eleve["questions"]]
    document.build(elements, onFirstPage=_pied_de_page, onLaterPages=_pied_de_page)
    return tampon.getvalue()
