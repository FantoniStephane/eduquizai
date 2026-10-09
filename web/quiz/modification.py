"""Lecture et contrôle du formulaire de modification d'un quiz (maquette 09).

Le formulaire n'est jamais cru sur parole : chaque question est reconstruite à
partir du quiz enregistré. Seuls les textes, la bonne réponse choisie et les
suppressions viennent de la requête. Le type d'une question, le nombre de ses
choix et les mots « Vrai » / « Faux » ne peuvent donc pas être modifiés.

Noms des champs : ``titre``, ``difficulte`` et, pour la question n° i
(à partir de 0) : ``q<i>-texte``, ``q<i>-explication``, ``q<i>-reponse``,
``q<i>-choix<j>``, ``q<i>-correct`` (numéro du bon choix) et ``q<i>-supprimer``.
"""

from .validation import (
    DIFFICULTES,
    EXPLICATION_MAX,
    TEXTE_MAX,
)

TITRE_MAX_SAISIE = 100
LIBELLES_TYPE = {
    "qcm": "QCM",
    "vrai_faux": "Vrai / Faux",
    "ouverte": "Question ouverte",
}


def vues_depuis_quiz(quiz):
    """Questions du quiz enregistré, prêtes à être affichées dans le formulaire."""
    vues = []
    for index, question in enumerate(quiz["questions"]):
        choix = question.get("choix") or []
        vues.append(
            {
                "index": index,
                "type_question": question["type_question"],
                "libelle_type": LIBELLES_TYPE[question["type_question"]],
                "texte": question.get("texte") or "",
                "explication": question.get("explication") or "",
                "reponse_attendue": question.get("reponse_attendue") or "",
                "choix": [
                    {"numero": j, "texte": c["texte"], "est_correct": c["est_correct"]}
                    for j, c in enumerate(choix)
                ],
                "supprimee": False,
                "erreurs": [],
            }
        )
    return vues


def _texte(donnees, nom):
    """Texte saisi, sans espaces superflus (chaîne vide s'il est absent)."""
    return str(donnees.get(nom, "")).strip()


def _controler_texte(valeur, maximum, vide, trop_long, erreurs):
    """Ajoute l'erreur adaptée si le texte est vide ou trop long."""
    if not valeur:
        erreurs.append(vide)
    elif len(valeur) > maximum:
        erreurs.append(trop_long)


def _lire_question(donnees, quiz_question, vue):
    """Applique à la vue d'une question les valeurs saisies et note les erreurs."""
    index = vue["index"]
    erreurs = vue["erreurs"]
    vue["texte"] = _texte(donnees, f"q{index}-texte")
    _controler_texte(
        vue["texte"],
        TEXTE_MAX,
        "L'énoncé est obligatoire.",
        f"L'énoncé ne doit pas dépasser {TEXTE_MAX} caractères.",
        erreurs,
    )
    if vue["type_question"] == "ouverte":
        vue["reponse_attendue"] = _texte(donnees, f"q{index}-reponse")
        _controler_texte(
            vue["reponse_attendue"],
            EXPLICATION_MAX,
            "La réponse attendue est obligatoire.",
            f"La réponse attendue ne doit pas dépasser {EXPLICATION_MAX} caractères.",
            erreurs,
        )
        # L'explication d'une question ouverte n'est pas modifiable (maquette 09)
        vue["explication"] = quiz_question["explication"]
        return
    vue["explication"] = _texte(donnees, f"q{index}-explication")
    _controler_texte(
        vue["explication"],
        EXPLICATION_MAX,
        "L'explication est obligatoire.",
        f"L'explication ne doit pas dépasser {EXPLICATION_MAX} caractères.",
        erreurs,
    )
    correct = _texte(donnees, f"q{index}-correct")
    bon_choix = int(correct) if correct.isdigit() else -1
    if not 0 <= bon_choix < len(vue["choix"]):
        erreurs.append("Choisissez la bonne réponse.")
    for choix in vue["choix"]:
        choix["est_correct"] = choix["numero"] == bon_choix
        if vue["type_question"] == "qcm":
            choix["texte"] = _texte(donnees, f"q{index}-choix{choix['numero']}")
            _controler_texte(
                choix["texte"],
                TEXTE_MAX,
                f"Le choix {choix['numero'] + 1} est vide.",
                f"Le choix {choix['numero'] + 1} est trop long.",
                erreurs,
            )


def lire_modification(donnees, quiz):
    """Lit le formulaire de modification et le contrôle.

    Args:
        donnees: données reçues (``request.POST``).
        quiz: quiz enregistré (dictionnaire), qui sert de modèle.

    Returns:
        Un dictionnaire : ``titre``, ``difficulte``, ``vues`` (questions telles
        qu'elles seront réaffichées, avec leurs erreurs), ``questions`` (à
        enregistrer, sans les questions supprimées), ``erreurs`` (erreurs
        générales) et ``valide`` (vrai si rien n'est à corriger).
    """
    erreurs = []
    titre = _texte(donnees, "titre")
    if not titre:
        erreurs.append("Le titre est obligatoire.")
    elif len(titre) > TITRE_MAX_SAISIE:
        erreurs.append(f"Le titre ne doit pas dépasser {TITRE_MAX_SAISIE} caractères.")
    difficulte = _texte(donnees, "difficulte")
    if difficulte not in DIFFICULTES:
        erreurs.append("Choisissez une difficulté.")

    vues = vues_depuis_quiz(quiz)
    questions = []
    for vue, ancienne in zip(vues, quiz["questions"], strict=True):
        if _texte(donnees, f"q{vue['index']}-supprimer") == "1":
            vue["supprimee"] = True
            continue
        _lire_question(donnees, ancienne, vue)
        questions.append(
            {
                "type_question": vue["type_question"],
                "texte": vue["texte"],
                "explication": vue["explication"],
                "reponse_attendue": vue["reponse_attendue"] or None,
                "choix": [
                    {"texte": c["texte"], "est_correct": c["est_correct"]}
                    for c in vue["choix"]
                ],
            }
        )
    if not questions:
        erreurs.append("Un quiz doit garder au moins une question.")
    valide = not erreurs and not any(vue["erreurs"] for vue in vues)
    return {
        "titre": titre,
        "difficulte": difficulte,
        "vues": vues,
        "questions": questions,
        "erreurs": erreurs,
        "valide": valide,
    }
