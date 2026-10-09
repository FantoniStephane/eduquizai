"""Import d'un fichier texte (.txt ou .docx) dans une leçon (tâche 32, maquette 04c).

Le fichier envoyé par le navigateur n'est jamais cru sur parole : son nom, sa
taille et son contenu réel sont contrôlés avant toute lecture. Le texte extrait
est converti en Markdown, le format de référence de la leçon (voir
``conversion.py``). Les images, les macros et la mise en page d'un .docx sont
ignorées : seuls le texte, les titres, le gras, l'italique et les listes sont gardés.
"""

import io
import logging
import zipfile

import mammoth

from .conversion import html_vers_markdown
from .forms import CONTENU_MAX

logger = logging.getLogger(__name__)

EXTENSIONS = (".txt", ".docx")
TAILLE_MAX = 5 * 1024 * 1024
# Protection contre la « bombe ZIP » : un petit .docx qui occuperait énormément
# de place une fois décompressé
ENTREES_MAX = 2_000
TAILLE_DECOMPRESSEE_MAX = 50 * 1024 * 1024


class ImportInvalideError(Exception):
    """Fichier refusé ; message destiné à l'enseignant, sans détail technique."""


def extraire_texte(nom, octets):
    """Contrôle un fichier importé et renvoie son texte en Markdown.

    Args:
        nom: nom du fichier envoyé (seule l'extension est utilisée).
        octets: contenu du fichier.

    Returns:
        Le texte en Markdown, prêt à être chargé dans l'éditeur.

    Raises:
        ImportInvalideError: extension, taille, contenu ou longueur non conformes.
    """
    extension = "." + str(nom).rsplit(".", 1)[-1].lower() if "." in str(nom) else ""
    if extension not in EXTENSIONS:
        raise ImportInvalideError(
            "Format non accepté : choisissez un fichier .docx ou .txt."
        )
    if not octets:
        raise ImportInvalideError("Le fichier est vide.")
    if len(octets) > TAILLE_MAX:
        raise ImportInvalideError("Le fichier dépasse la taille maximale de 5 Mo.")
    if extension == ".txt":
        texte = _lire_txt(octets)
    else:
        texte = _lire_docx(octets)
    if not texte:
        raise ImportInvalideError("Le fichier ne contient aucun texte.")
    if len(texte) > CONTENU_MAX:
        raise ImportInvalideError(
            f"Le texte dépasse {CONTENU_MAX:,} caractères".replace(",", " ")
            + " : raccourcissez le fichier."
        )
    return texte


def _lire_txt(octets):
    """Texte d'un fichier .txt (UTF-8, sinon encodage Windows)."""
    if octets.startswith(b"PK") or b"\x00" in octets:
        raise ImportInvalideError("Ce fichier n'est pas un fichier texte.")
    try:
        texte = octets.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            texte = octets.decode("cp1252")
        except UnicodeDecodeError:
            raise ImportInvalideError(
                "L'encodage du fichier n'est pas reconnu : enregistrez-le en UTF-8."
            ) from None
    return "\n".join(ligne.rstrip() for ligne in texte.splitlines()).strip()


def _controler_archive(octets):
    """Vérifie que le fichier est une vraie archive Word de taille raisonnable."""
    try:
        with zipfile.ZipFile(io.BytesIO(octets)) as archive:
            entrees = archive.infolist()
            noms = {entree.filename for entree in entrees}
            if not {"[Content_Types].xml", "word/document.xml"} <= noms:
                raise ImportInvalideError("Ce fichier n'est pas un document Word.")
            if len(entrees) > ENTREES_MAX:
                raise ImportInvalideError("Le document Word n'est pas valide.")
            if sum(entree.file_size for entree in entrees) > TAILLE_DECOMPRESSEE_MAX:
                raise ImportInvalideError("Le document Word est trop volumineux.")
    except zipfile.BadZipFile:
        raise ImportInvalideError("Ce fichier n'est pas un document Word.") from None


def _lire_docx(octets):
    """Texte d'un document Word, converti en Markdown (images ignorées)."""
    _controler_archive(octets)
    try:
        resultat = mammoth.convert_to_html(
            io.BytesIO(octets), convert_image=lambda image: []
        )
    except Exception:
        logger.exception("Import : lecture du document Word impossible")
        raise ImportInvalideError(
            "Le document Word n'a pas pu être lu : il est peut-être abîmé."
        ) from None
    return html_vers_markdown(resultat.value)
