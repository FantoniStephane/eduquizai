"""Export d'un quiz en PDF, version élève (tâche 40).

Seule la version élève est exportée : le corrigé (bonnes réponses,
explications, réponse attendue) reste dans l'espace de l'enseignant. La
fonction qui dessine le PDF ne reçoit que le résultat de ``version_eleve`` :
les réponses ne peuvent donc pas se retrouver dans le fichier, même par
erreur.

Mise en page aux couleurs de l'application (charte graphique), sans logo ni
mention de l'outil : le document est celui de l'enseignant, remis à ses élèves.
Police Helvetica intégrée aux lecteurs PDF (aucun fichier de police embarqué) :
le fichier reste léger et net à l'impression.
"""

from functools import partial
from io import BytesIO
from xml.sax.saxutils import escape

from django.utils.text import slugify
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
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
    "<b>Consigne :</b> pour les QCM et les Vrai / Faux, cochez la bonne réponse. "
    "Pour les questions ouvertes, répondez sur les lignes."
)

LIBELLES_TYPE = {
    "qcm": "QCM",
    "vrai_faux": "VRAI / FAUX",
    "ouverte": "QUESTION OUVERTE",
}

# Couleurs de la charte (variables de style.css)
_PRIMAIRE = HexColor("#1D4ED8")
_PRIMAIRE_FONCE = HexColor("#1E3A8A")
_PRIMAIRE_CLAIR = HexColor("#EFF6FF")
_TEXTE = HexColor("#0F172A")
_GRIS = HexColor("#64748B")
_BORDURE = HexColor("#E2E8F0")
_FOND = HexColor("#F8FAFC")

_MARGE = 16 * mm
_LARGEUR_UTILE = A4[0] - 2 * _MARGE


def _style(nom, police="Helvetica", taille=10.5, interligne=14, couleur=_TEXTE):
    """Style de paragraphe (raccourci)."""
    return ParagraphStyle(
        nom, fontName=police, fontSize=taille, leading=interligne, textColor=couleur
    )


_STYLES = {
    "titre": _style("titre", "Helvetica-Bold", 20, 24, _PRIMAIRE_FONCE),
    "consigne": _style("consigne", taille=9.5, interligne=13, couleur=_PRIMAIRE_FONCE),
    "type": _style("type", "Helvetica-Bold", 7.5, 10, _PRIMAIRE),
    "question": _style("question", "Helvetica-Bold", 11, 14.5),
    "choix": _style("choix"),
    "identite": _style("identite", taille=9, interligne=11, couleur=_GRIS),
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

    Le préfixe « quiz- » n'est pas doublé quand le titre commence déjà par
    « Quiz » (titres proposés par la génération : « Quiz — … »).

    Args:
        quiz: quiz lu dans MongoDB.

    Returns:
        str: nom sans accent ni caractère spécial.
    """
    nom = slugify(quiz["titre"])[:80].strip("-") or "eleve"
    if nom != "quiz" and not nom.startswith("quiz-"):
        nom = f"quiz-{nom}"
    return f"{nom}.pdf"


def _texte(valeur):
    """Échappe un texte pour ReportLab, qui lit une forme de balisage XML.

    Sans cela, un « < » écrit par l'IA ou l'enseignant casserait le PDF ou
    serait interprété comme une balise.
    """
    return escape(valeur).replace("\n", "<br/>")


class _CanevasNumerote(Canvas):
    """Canevas qui connaît le nombre total de pages (« Page 1 / 2 »).

    Les pages sont mises de côté puis dessinées à la fin, quand le total est
    connu.
    """

    def __init__(self, *args, titre_quiz="", **kwargs):
        super().__init__(*args, **kwargs)
        self._titre_quiz = titre_quiz
        self._pages = []

    def showPage(self):  # noqa: N802 (nom imposé par ReportLab)
        """Garde la page au lieu de l'écrire tout de suite."""
        self._pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        """Écrit chaque page avec son pied de page, puis le fichier."""
        total = len(self._pages)
        for page in self._pages:
            self.__dict__.update(page)
            self._pied_de_page(total)
            super().showPage()
        super().save()

    def _pied_de_page(self, total):
        """Filet, titre du quiz (feuilles mélangées) et numéro de page."""
        self.saveState()
        self.setStrokeColor(_BORDURE)
        self.setLineWidth(0.6)
        self.line(_MARGE, 14 * mm, A4[0] - _MARGE, 14 * mm)
        self.setFont("Helvetica", 8)
        self.setFillColor(_GRIS)
        titre = self._titre_quiz
        largeur_max = _LARGEUR_UTILE - 25 * mm
        while titre and self.stringWidth(titre, "Helvetica", 8) > largeur_max:
            titre = titre[:-2] + "…"
        self.drawString(_MARGE, 8.5 * mm, titre)
        self.drawRightString(
            A4[0] - _MARGE, 8.5 * mm, f"Page {self._pageNumber} / {total}"
        )
        self.restoreState()


class _Pastilles(Flowable):
    """Pastilles arrondies : matière, niveau, nombre de questions."""

    TAILLE = 8.5

    def __init__(self, libelles):
        super().__init__()
        self.libelles = libelles

    def wrap(self, largeur, hauteur):
        """Une ligne de pastilles."""
        self.width, self.height = largeur, 6 * mm
        return self.width, self.height

    def draw(self):
        """Fond bleu clair, texte bleu."""
        canvas = self.canv
        x = 0
        for libelle in self.libelles:
            largeur = canvas.stringWidth(libelle, "Helvetica-Bold", self.TAILLE)
            largeur += 6 * mm
            canvas.setFillColor(_PRIMAIRE_CLAIR)
            canvas.roundRect(x, 0, largeur, 6 * mm, 3 * mm, stroke=0, fill=1)
            canvas.setFillColor(_PRIMAIRE)
            canvas.setFont("Helvetica-Bold", self.TAILLE)
            canvas.drawCentredString(x + largeur / 2, 2 * mm, libelle)
            x += largeur + 2 * mm


class _Champ(Flowable):
    """Champ à remplir : libellé puis ligne d'écriture."""

    def __init__(self, libelle):
        super().__init__()
        self.libelle = libelle

    def wrap(self, largeur, hauteur):
        """Hauteur d'une ligne d'écriture."""
        self.width, self.height = largeur, 8 * mm
        return self.width, self.height

    def draw(self):
        """Libellé en gris, ligne pleine claire."""
        canvas = self.canv
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(_GRIS)
        canvas.drawString(0, 1.6 * mm, self.libelle)
        debut = canvas.stringWidth(self.libelle, "Helvetica", 9) + 2 * mm
        canvas.setStrokeColor(HexColor("#CBD5E1"))
        canvas.setLineWidth(0.6)
        canvas.line(debut, 1 * mm, self.width, 1 * mm)


NOTE_SUR = 20
"""Barème de la note, l'habitude des enseignants (2 points par question pour 10)."""


class _Note(Flowable):
    """Case de la note sur 20, en haut à droite du cadre d'identité."""

    def __init__(self, total=NOTE_SUR):
        super().__init__()
        self.total = total

    def wrap(self, largeur, hauteur):
        """Carré de la hauteur du cadre."""
        self.width, self.height = largeur, 17 * mm
        return self.width, self.height

    def draw(self):
        """Cadre blanc, « Note » au-dessus, « / total » en bas à droite."""
        canvas = self.canv
        canvas.setFillColor(white)
        canvas.setStrokeColor(_BORDURE)
        canvas.roundRect(0, 0, self.width, self.height, 2.5 * mm, stroke=1, fill=1)
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.setFillColor(_GRIS)
        canvas.drawCentredString(self.width / 2, self.height - 4.5 * mm, "NOTE")
        canvas.setFont("Helvetica-Bold", 11)
        canvas.setFillColor(_PRIMAIRE_FONCE)
        canvas.drawRightString(self.width - 3 * mm, 3 * mm, f"/ {self.total}")


class _Numero(Flowable):
    """Pastille ronde portant le numéro de la question."""

    DIAMETRE = 7.4 * mm

    def __init__(self, numero):
        super().__init__()
        self.numero = numero

    def wrap(self, largeur, hauteur):
        """Taille du rond."""
        return self.DIAMETRE, self.DIAMETRE

    def draw(self):
        """Rond bleu foncé, numéro blanc."""
        rayon = self.DIAMETRE / 2
        self.canv.setFillColor(_PRIMAIRE_FONCE)
        self.canv.circle(rayon, rayon, rayon, stroke=0, fill=1)
        self.canv.setFillColor(white)
        self.canv.setFont("Helvetica-Bold", 10)
        self.canv.drawCentredString(rayon, rayon - 1.25 * mm, str(self.numero))


class _Choix(Flowable):
    """Case à cocher arrondie, lettre éventuelle, puis libellé du choix."""

    COTE = 3.8 * mm

    def __init__(self, libelle, lettre=""):
        super().__init__()
        self.lettre = lettre
        self.retrait = 13 * mm if lettre else 7 * mm
        self.paragraphe = Paragraph(_texte(libelle), _STYLES["choix"])

    def wrap(self, largeur, hauteur):
        """Calcule la place occupée par le libellé (retour à la ligne compris)."""
        _, hauteur_texte = self.paragraphe.wrap(largeur - self.retrait, hauteur)
        self.width, self.height = largeur, hauteur_texte
        return self.width, self.height

    def draw(self):
        """Case alignée sur la première ligne, lettre, libellé."""
        canvas = self.canv
        base = self.height - _STYLES["choix"].leading
        canvas.setStrokeColor(_PRIMAIRE)
        canvas.setFillColor(white)
        canvas.setLineWidth(0.9)
        canvas.roundRect(0, base + 0.5 * mm, self.COTE, self.COTE, 1 * mm, 1, 1)
        if self.lettre:
            canvas.setFont("Helvetica-Bold", 10.5)
            canvas.setFillColor(_PRIMAIRE)
            canvas.drawString(7 * mm, base + 1.1 * mm, f"{self.lettre}.")
        self.paragraphe.drawOn(canvas, self.retrait, 0)


class _Lignes(Flowable):
    """Lignes pour écrire la réponse à une question ouverte."""

    ECART = 8 * mm

    def __init__(self, nombre):
        super().__init__()
        self.nombre = nombre

    def wrap(self, largeur, hauteur):
        """Une hauteur fixe par ligne."""
        self.width, self.height = largeur, self.nombre * self.ECART
        return self.width, self.height

    def draw(self):
        """Lignes pleines, claires."""
        self.canv.setStrokeColor(HexColor("#CBD5E1"))
        self.canv.setLineWidth(0.6)
        for rang in range(self.nombre):
            y = rang * self.ECART + 1 * mm
            self.canv.line(0, y, self.width, y)


def _identite():
    """Cadre « Nom / Prénom / Classe / Date » et case de la note."""
    largeur_note = 26 * mm
    largeur_champs = _LARGEUR_UTILE - largeur_note - 14 * mm
    demi = largeur_champs / 2
    champs = Table(
        [
            [_Champ("Nom"), _Champ("Prénom")],
            [_Champ("Classe"), _Champ("Date")],
        ],
        colWidths=[demi, demi],
    )
    champs.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 0.5 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5 * mm),
            ]
        )
    )
    cadre = Table(
        [[champs, _Note()]],
        colWidths=[_LARGEUR_UTILE - largeur_note, largeur_note],
        cornerRadii=[3 * mm] * 4,
    )
    cadre.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _FOND),
                ("BOX", (0, 0), (-1, -1), 0.6, _BORDURE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 5 * mm),
                ("RIGHTPADDING", (-1, 0), (-1, 0), 3.5 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5 * mm),
            ]
        )
    )
    return cadre


def _consigne():
    """Encart de consigne, barre bleue à gauche (comme les explications)."""
    encart = Table(
        [["", Paragraph(CONSIGNE, _STYLES["consigne"])]],
        colWidths=[1.2 * mm, _LARGEUR_UTILE - 1.2 * mm],
    )
    encart.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), _PRIMAIRE),
                ("BACKGROUND", (1, 0), (1, 0), _PRIMAIRE_CLAIR),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 0),
                ("LEFTPADDING", (1, 0), (1, 0), 4 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ]
        )
    )
    return encart


def _question(question):
    """Carte d'une question, gardée sur une même page."""
    interieur = _LARGEUR_UTILE - 10 * mm
    entete = Table(
        [
            [
                _Numero(question["numero"]),
                [
                    Paragraph(
                        LIBELLES_TYPE[question["type_question"]], _STYLES["type"]
                    ),
                    Paragraph(_texte(question["texte"]), _STYLES["question"]),
                ],
            ]
        ],
        colWidths=[10 * mm, interieur - 10 * mm],
    )
    entete.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    contenu = [entete, Spacer(1, 3 * mm)]
    if question["type_question"] == "ouverte":
        contenu.append(_Lignes(LIGNES_REPONSE))
    else:
        lettres = "ABCDEF" if question["type_question"] == "qcm" else ""
        for rang, libelle in enumerate(question["choix"]):
            lettre = lettres[rang] if lettres else ""
            contenu += [_Choix(libelle, lettre), Spacer(1, 1.8 * mm)]
    carte = Table([[contenu]], colWidths=[_LARGEUR_UTILE], cornerRadii=[3 * mm] * 4)
    carte.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, _BORDURE),
                ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
            ]
        )
    )
    return KeepTogether([carte, Spacer(1, 4 * mm)])


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
    total = len(eleve["questions"])
    tampon = BytesIO()
    document = SimpleDocTemplate(
        tampon,
        pagesize=A4,
        leftMargin=_MARGE,
        rightMargin=_MARGE,
        topMargin=16 * mm,
        bottomMargin=20 * mm,
        title=eleve["titre"],
        author="",
        creator="EduQuizAI",
    )
    pastilles = [valeur for valeur in (matiere, niveau) if valeur]
    pastilles.append(f"{total} question{'s' if total > 1 else ''}")
    elements = [
        Paragraph(_texte(eleve["titre"]), _STYLES["titre"]),
        Spacer(1, 2.5 * mm),
        _Pastilles(pastilles),
        Spacer(1, 5 * mm),
        _identite(),
        Spacer(1, 4 * mm),
        _consigne(),
        Spacer(1, 6 * mm),
    ]
    elements += [_question(question) for question in eleve["questions"]]
    document.build(
        elements,
        canvasmaker=partial(_CanevasNumerote, titre_quiz=eleve["titre"]),
    )
    return tampon.getvalue()
