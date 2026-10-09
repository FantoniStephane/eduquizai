"""Contrôle d'un quiz avant son écriture dans MongoDB.

MongoDB n'impose aucune structure par défaut : ce module joue le rôle des
contraintes d'une base relationnelle. Il vérifie les champs du quiz et les
règles propres à chaque type de question (QCM, vrai/faux, question ouverte).
Une règle de validation $jsonSchema posée sur la collection (voir schema.py)
sert de seconde barrière, côté base.
"""

DIFFICULTES = ("facile", "moyen", "difficile")
STATUTS = ("brouillon", "valide")
TYPES_QUESTION = ("qcm", "vrai_faux", "ouverte")

TITRE_MAX = 200
DESCRIPTION_MAX = 500
QUESTIONS_MAX = 20
TEXTE_MAX = 1000
EXPLICATION_MAX = 2000
CHOIX_QCM_MIN = 3
CHOIX_QCM_MAX = 6
CHOIX_VRAI_FAUX = ("Vrai", "Faux")


class QuizInvalideError(ValueError):
    """Le quiz ne respecte pas la structure attendue.

    Attributes:
        erreurs: liste des problèmes détectés, en français.
    """

    def __init__(self, erreurs):
        super().__init__("; ".join(erreurs))
        self.erreurs = erreurs


def _texte_valide(valeur, maximum, obligatoire=True):
    """Indique si la valeur est une chaîne de longueur acceptable."""
    if not isinstance(valeur, str):
        return False
    if obligatoire and not valeur.strip():
        return False
    return len(valeur) <= maximum


def _erreurs_question(numero, question):
    """Liste les erreurs d'une question (numérotée à partir de 1)."""
    if not isinstance(question, dict):
        return [f"Question {numero} : format invalide."]
    erreurs = []
    prefixe = f"Question {numero}"
    type_question = question.get("type_question")
    if type_question not in TYPES_QUESTION:
        return [f"{prefixe} : type inconnu."]
    if not _texte_valide(question.get("texte"), TEXTE_MAX):
        erreurs.append(f"{prefixe} : énoncé vide ou trop long.")
    if not _texte_valide(question.get("explication"), EXPLICATION_MAX):
        erreurs.append(f"{prefixe} : explication vide ou trop longue.")

    choix = question.get("choix")
    if not isinstance(choix, list) or not all(
        isinstance(c, dict)
        and _texte_valide(c.get("texte"), TEXTE_MAX)
        and isinstance(c.get("est_correct"), bool)
        for c in choix
    ):
        return [*erreurs, f"{prefixe} : choix mal formés."]
    nb_corrects = sum(c["est_correct"] for c in choix)

    if type_question == "qcm":
        if not CHOIX_QCM_MIN <= len(choix) <= CHOIX_QCM_MAX:
            erreurs.append(
                f"{prefixe} : un QCM propose de {CHOIX_QCM_MIN} "
                f"à {CHOIX_QCM_MAX} choix."
            )
        if nb_corrects != 1:
            erreurs.append(f"{prefixe} : un QCM a une seule bonne réponse.")
    elif type_question == "vrai_faux":
        if tuple(c["texte"] for c in choix) != CHOIX_VRAI_FAUX or nb_corrects != 1:
            erreurs.append(
                f"{prefixe} : un vrai/faux propose « Vrai » et « Faux », "
                "dont un seul est correct."
            )
    else:  # question ouverte
        if choix:
            erreurs.append(f"{prefixe} : une question ouverte n'a pas de choix.")
        if not _texte_valide(question.get("reponse_attendue"), EXPLICATION_MAX):
            erreurs.append(f"{prefixe} : réponse attendue manquante.")
    return erreurs


def valider_questions(questions):
    """Contrôle la liste des questions d'un quiz.

    Args:
        questions: liste de dictionnaires (texte, type_question, explication,
            reponse_attendue, choix).

    Raises:
        QuizInvalideError: si au moins une règle n'est pas respectée.
    """
    if not isinstance(questions, list) or not 1 <= len(questions) <= QUESTIONS_MAX:
        raise QuizInvalideError([f"Un quiz contient de 1 à {QUESTIONS_MAX} questions."])
    erreurs = []
    for numero, question in enumerate(questions, start=1):
        erreurs += _erreurs_question(numero, question)
    if erreurs:
        raise QuizInvalideError(erreurs)


def valider_quiz(document):
    """Contrôle un document quiz complet avant son écriture.

    Args:
        document: dictionnaire du quiz tel qu'il sera enregistré.

    Raises:
        QuizInvalideError: si au moins une règle n'est pas respectée.
    """
    erreurs = []
    if not _texte_valide(document.get("titre"), TITRE_MAX):
        erreurs.append("Titre vide ou trop long.")
    if not _texte_valide(document.get("description"), DESCRIPTION_MAX, False):
        erreurs.append("Description trop longue.")
    if document.get("difficulte") not in DIFFICULTES:
        erreurs.append("Difficulté inconnue.")
    if document.get("statut") not in STATUTS:
        erreurs.append("Statut inconnu.")
    for champ in ("id_lecon", "id_utilisateur"):
        valeur = document.get(champ)
        if not isinstance(valeur, int) or isinstance(valeur, bool) or valeur < 1:
            erreurs.append(f"Identifiant {champ} invalide.")
    try:
        valider_questions(document.get("questions"))
    except QuizInvalideError as exc:
        erreurs += exc.erreurs
    if erreurs:
        raise QuizInvalideError(erreurs)
