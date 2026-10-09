"""Accès aux quiz enregistrés dans MongoDB (patron Repository).

Les vues ne manipulent jamais PyMongo directement : elles passent par ce
repository, qui applique toujours les mêmes règles.

- Chaque lecture et chaque écriture filtre sur l'enseignant propriétaire :
  le quiz d'un collègue est traité comme inexistant (protection IDOR).
- Le document est contrôlé (validation.py) avant toute écriture.
- Les identifiants reçus sont convertis en types simples (int, ObjectId) :
  un dictionnaire comme {"$ne": None} ne peut pas se glisser dans un filtre
  (injection NoSQL).
"""

import re

from bson import ObjectId
from bson.errors import InvalidId
from django.utils import timezone
from pymongo import DESCENDING

from .mongo import get_db
from .schema import NOM_COLLECTION
from .validation import valider_quiz


def _object_id(id_quiz):
    """Convertit l'identifiant reçu dans l'URL en ObjectId (None s'il est invalide)."""
    try:
        return ObjectId(str(id_quiz))
    except InvalidId:
        return None


def _preparer_questions(questions):
    """Normalise les questions : ordre d'affichage et champs facultatifs."""
    return [
        {
            "ordre": ordre,
            "type_question": question.get("type_question"),
            "texte": question.get("texte"),
            "explication": question.get("explication"),
            "reponse_attendue": question.get("reponse_attendue"),
            "choix": [
                {"texte": choix.get("texte"), "est_correct": choix.get("est_correct")}
                for choix in question.get("choix") or []
                if isinstance(choix, dict)
            ],
        }
        if isinstance(question, dict)
        else question
        for ordre, question in enumerate(questions or [], start=1)
    ]


def _vers_python(document):
    """Ajoute l'identifiant sous forme de texte (« id ») pour les gabarits."""
    if document is not None:
        document["id"] = str(document["_id"])
    return document


class QuizRepository:
    """Opérations sur la collection « quiz », toujours limitées au propriétaire."""

    def __init__(self, db=None):
        """Utilise la base de l'application, ou celle fournie (tests)."""
        self.collection = (get_db() if db is None else db)[NOM_COLLECTION]

    def _filtre(self, id_quiz, id_utilisateur):
        """Filtre d'un quiz précis appartenant à l'enseignant (None si id invalide)."""
        identifiant = _object_id(id_quiz)
        if identifiant is None:
            return None
        return {"_id": identifiant, "id_utilisateur": int(id_utilisateur)}

    def creer(
        self, *, id_utilisateur, id_lecon, titre, difficulte, questions, description=""
    ):
        """Enregistre un quiz généré, toujours au statut « brouillon ».

        Returns:
            L'identifiant du nouveau quiz (texte).

        Raises:
            QuizInvalideError: si le quiz ne respecte pas la structure attendue.
        """
        document = {
            "titre": titre,
            "description": description,
            "difficulte": difficulte,
            "statut": "brouillon",
            "date_creation": timezone.now(),
            "date_validation": None,
            "id_lecon": int(id_lecon),
            "id_utilisateur": int(id_utilisateur),
            "questions": _preparer_questions(questions),
        }
        valider_quiz(document)
        return str(self.collection.insert_one(document).inserted_id)

    def obtenir(self, id_quiz, id_utilisateur):
        """Retourne le quiz s'il appartient à l'enseignant, sinon None."""
        filtre = self._filtre(id_quiz, id_utilisateur)
        if filtre is None:
            return None
        return _vers_python(self.collection.find_one(filtre))

    def lister(
        self, id_utilisateur, *, statut=None, id_lecon=None, recherche=None, limite=None
    ):
        """Quiz de l'enseignant, du plus récent au plus ancien, filtres facultatifs.

        Args:
            id_utilisateur: enseignant connecté.
            statut: « brouillon » ou « valide ».
            id_lecon: limite aux quiz d'une leçon.
            recherche: texte cherché dans le titre (sans tenir compte de la casse).
            limite: nombre maximal de quiz renvoyés (tous si absent).
        """
        filtre = {"id_utilisateur": int(id_utilisateur)}
        if statut:
            filtre["statut"] = str(statut)
        if id_lecon:
            filtre["id_lecon"] = int(id_lecon)
        if recherche:
            # Texte échappé : les caractères spéciaux des expressions régulières
            # sont cherchés tels quels
            filtre["titre"] = {"$regex": re.escape(str(recherche)), "$options": "i"}
        # _id en second critère : ordre stable si deux quiz ont la même date
        curseur = self.collection.find(filtre).sort(
            [("date_creation", DESCENDING), ("_id", DESCENDING)]
        )
        if limite:
            curseur = curseur.limit(int(limite))
        return [_vers_python(document) for document in curseur]

    def compter(self, id_utilisateur, statut=None):
        """Nombre de quiz de l'enseignant, éventuellement d'un seul statut."""
        filtre = {"id_utilisateur": int(id_utilisateur)}
        if statut:
            filtre["statut"] = str(statut)
        return self.collection.count_documents(filtre)

    def compter_par_lecon(self, id_lecon, id_utilisateur):
        """Nombre de quiz générés à partir d'une leçon de l'enseignant."""
        return self.collection.count_documents(
            {"id_lecon": int(id_lecon), "id_utilisateur": int(id_utilisateur)}
        )

    def modifier(
        self,
        id_quiz,
        id_utilisateur,
        *,
        titre,
        description,
        questions,
        difficulte=None,
    ):
        """Remplace le titre, la description, les questions (et la difficulté).

        Un quiz modifié repasse toujours en brouillon : il doit être relu puis
        validé à nouveau par l'enseignant.

        Returns:
            True si le quiz a été trouvé et modifié, False sinon.

        Raises:
            QuizInvalideError: si le quiz modifié ne respecte pas la structure.
        """
        quiz = self.obtenir(id_quiz, id_utilisateur)
        if quiz is None:
            return False
        modifications = {
            "titre": titre,
            "description": description,
            "questions": _preparer_questions(questions),
            "statut": "brouillon",
            "date_validation": None,
        }
        if difficulte is not None:
            modifications["difficulte"] = difficulte
        quiz.pop("id")
        valider_quiz({**quiz, **modifications})
        self.collection.update_one(
            self._filtre(id_quiz, id_utilisateur), {"$set": modifications}
        )
        return True

    def valider(self, id_quiz, id_utilisateur):
        """Passe un quiz en brouillon au statut « valide » (relu par l'enseignant).

        Returns:
            True si le quiz a été validé, False s'il est introuvable ou déjà validé.
        """
        filtre = self._filtre(id_quiz, id_utilisateur)
        if filtre is None:
            return False
        resultat = self.collection.update_one(
            {**filtre, "statut": "brouillon"},
            {"$set": {"statut": "valide", "date_validation": timezone.now()}},
        )
        return resultat.modified_count == 1

    def supprimer(self, id_quiz, id_utilisateur):
        """Supprime un quiz de l'enseignant.

        Returns:
            True si le quiz a été supprimé, False s'il est introuvable.
        """
        filtre = self._filtre(id_quiz, id_utilisateur)
        if filtre is None:
            return False
        return self.collection.delete_one(filtre).deleted_count == 1

    def supprimer_par_utilisateur(self, id_utilisateur):
        """Supprime tous les quiz d'un enseignant (suppression de son compte).

        Returns:
            Le nombre de quiz supprimés.
        """
        resultat = self.collection.delete_many({"id_utilisateur": int(id_utilisateur)})
        return resultat.deleted_count
