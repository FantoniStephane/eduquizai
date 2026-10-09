"""Contrôle des paramètres de génération et de la réponse du modèle.

Un modèle de langage peut se tromper : mauvais nombre de questions, deux
bonnes réponses, choix manquants… Sa réponse est donc vérifiée et mise en
forme avant d'être renvoyée à l'application web, qui la contrôlera encore
avant de l'enregistrer.
"""

import json

DIFFICULTES = ("facile", "moyen", "difficile")
TYPES_QUESTION = ("qcm", "vrai_faux", "ouverte")
NOMBRE_MIN = 3
NOMBRE_MAX = 20
CONTENU_MAX = 20_000
TEXTE_MAX = 1000
EXPLICATION_MAX = 2000
CHOIX_QCM = 4


class ParametresInvalidesError(ValueError):
    """Les paramètres de la demande de génération sont incorrects."""


class ReponseInvalideError(ValueError):
    """La réponse du modèle ne correspond pas au quiz demandé."""


def verifier_parametres(contenu, difficulte, types, nombre):
    """Vérifie la demande avant d'interroger le modèle.

    Raises:
        ParametresInvalidesError: si un paramètre est absent ou hors limites.
    """
    if not isinstance(contenu, str) or not contenu.strip():
        raise ParametresInvalidesError("Le contenu de la leçon est vide.")
    if len(contenu) > CONTENU_MAX:
        raise ParametresInvalidesError("Le contenu de la leçon est trop long.")
    if difficulte not in DIFFICULTES:
        raise ParametresInvalidesError("Difficulté inconnue.")
    if (
        not isinstance(types, list | tuple)
        or not types
        or any(t not in TYPES_QUESTION for t in types)
    ):
        raise ParametresInvalidesError("Types de questions invalides.")
    if (
        not isinstance(nombre, int)
        or isinstance(nombre, bool)
        or not NOMBRE_MIN <= nombre <= NOMBRE_MAX
    ):
        raise ParametresInvalidesError(
            f"Le nombre de questions doit être compris entre {NOMBRE_MIN} "
            f"et {NOMBRE_MAX}."
        )


def _texte(valeur, maximum, champ, numero):
    """Retourne le texte nettoyé, ou lève une erreur s'il est vide ou trop long."""
    if not isinstance(valeur, str) or not valeur.strip():
        raise ReponseInvalideError(f"Question {numero} : {champ} manquant.")
    valeur = valeur.strip()
    if len(valeur) > maximum:
        raise ReponseInvalideError(f"Question {numero} : {champ} trop long.")
    return valeur


def _choix(question, numero):
    """Liste des choix (texte nettoyé et booléen), ou erreur si mal formés."""
    choix = question.get("choix")
    if not isinstance(choix, list):
        raise ReponseInvalideError(f"Question {numero} : choix manquants.")
    resultat = []
    for element in choix:
        if not isinstance(element, dict) or not isinstance(
            element.get("est_correct"), bool
        ):
            raise ReponseInvalideError(f"Question {numero} : choix mal formé.")
        texte = _texte(element.get("texte"), TEXTE_MAX, "choix", numero)
        resultat.append({"texte": texte, "est_correct": element["est_correct"]})
    return resultat


def _question(question, numero, types):
    """Contrôle et met en forme une question selon son type."""
    if not isinstance(question, dict):
        raise ReponseInvalideError(f"Question {numero} : format invalide.")
    type_question = question.get("type_question")
    if type_question not in types:
        raise ReponseInvalideError(f"Question {numero} : type non demandé.")
    propre = {
        "type_question": type_question,
        "texte": _texte(question.get("texte"), TEXTE_MAX, "énoncé", numero),
        "explication": _texte(
            question.get("explication"), EXPLICATION_MAX, "explication", numero
        ),
        "reponse_attendue": None,
        "choix": [],
    }
    if type_question == "ouverte":
        propre["reponse_attendue"] = _texte(
            question.get("reponse_attendue"),
            EXPLICATION_MAX,
            "réponse attendue",
            numero,
        )
        return propre

    choix = _choix(question, numero)
    if sum(c["est_correct"] for c in choix) != 1:
        raise ReponseInvalideError(
            f"Question {numero} : il faut exactement une bonne réponse."
        )
    if type_question == "qcm":
        if len(choix) != CHOIX_QCM:
            raise ReponseInvalideError(
                f"Question {numero} : un QCM propose {CHOIX_QCM} choix."
            )
        propre["choix"] = choix
    else:  # vrai/faux : libellés remis dans la forme attendue
        if sorted(c["texte"].lower() for c in choix) != ["faux", "vrai"]:
            raise ReponseInvalideError(
                f"Question {numero} : un vrai/faux propose « Vrai » et « Faux »."
            )
        vrai_correct = next(c for c in choix if c["texte"].lower() == "vrai")[
            "est_correct"
        ]
        propre["choix"] = [
            {"texte": "Vrai", "est_correct": vrai_correct},
            {"texte": "Faux", "est_correct": not vrai_correct},
        ]
    return propre


def valider_reponse(brut, types, nombre):
    """Analyse le texte JSON renvoyé par le modèle et contrôle chaque question.

    Args:
        brut: texte renvoyé par le modèle.
        types: types de questions demandés.
        nombre: nombre de questions demandé.

    Returns:
        La liste des questions, nettoyées et mises en forme.

    Raises:
        ReponseInvalideError: si le JSON est illisible ou ne correspond pas
            à la demande.
    """
    try:
        donnees = json.loads(brut)
    except (TypeError, ValueError) as exc:
        raise ReponseInvalideError("La réponse du modèle n'est pas du JSON.") from exc
    questions = donnees.get("questions") if isinstance(donnees, dict) else None
    if not isinstance(questions, list):
        raise ReponseInvalideError("La réponse ne contient pas de questions.")
    if len(questions) != nombre:
        raise ReponseInvalideError(
            f"{len(questions)} questions reçues au lieu de {nombre}."
        )
    return [
        _question(question, numero, types)
        for numero, question in enumerate(questions, start=1)
    ]
