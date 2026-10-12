"""Règle de validation et index de la collection « quiz » dans MongoDB.

La règle $jsonSchema est appliquée par MongoDB lui-même : un document mal
formé est refusé même s'il est écrit sans passer par le repository. Elle
complète le contrôle détaillé fait en Python (validation.py).
"""

from pymongo import ASCENDING, DESCENDING

from .validation import (
    CHOIX_QCM_MAX,
    DESCRIPTION_MAX,
    DIFFICULTES,
    EXPLICATION_MAX,
    QUESTIONS_MAX,
    STATUTS,
    TEXTE_MAX,
    TITRE_MAX,
    TYPES_QUESTION,
)

NOM_COLLECTION = "quiz"

_TEXTE = {"bsonType": "string", "maxLength": TEXTE_MAX}
_ENTIER = {"bsonType": ["int", "long"], "minimum": 1}

SCHEMA_QUIZ = {
    "bsonType": "object",
    "additionalProperties": False,
    "required": [
        "titre",
        "description",
        "difficulte",
        "statut",
        "date_creation",
        "date_validation",
        "id_lecon",
        "id_utilisateur",
        "questions",
    ],
    "properties": {
        "_id": {"bsonType": "objectId"},
        "titre": {"bsonType": "string", "minLength": 1, "maxLength": TITRE_MAX},
        "description": {"bsonType": "string", "maxLength": DESCRIPTION_MAX},
        "difficulte": {"enum": list(DIFFICULTES)},
        "statut": {"enum": list(STATUTS)},
        "date_creation": {"bsonType": "date"},
        "date_validation": {"bsonType": ["date", "null"]},
        "id_lecon": _ENTIER,
        "id_utilisateur": _ENTIER,
        "questions": {
            "bsonType": "array",
            "minItems": 1,
            "maxItems": QUESTIONS_MAX,
            "items": {
                "bsonType": "object",
                "additionalProperties": False,
                "required": ["ordre", "type_question", "texte", "explication", "choix"],
                "properties": {
                    "ordre": _ENTIER,
                    "type_question": {"enum": list(TYPES_QUESTION)},
                    "texte": _TEXTE,
                    "explication": {"bsonType": "string", "maxLength": EXPLICATION_MAX},
                    "reponse_attendue": {
                        "bsonType": ["string", "null"],
                        "maxLength": EXPLICATION_MAX,
                    },
                    "choix": {
                        "bsonType": "array",
                        "maxItems": CHOIX_QCM_MAX,
                        "items": {
                            "bsonType": "object",
                            "additionalProperties": False,
                            "required": ["texte", "est_correct"],
                            "properties": {
                                "texte": _TEXTE,
                                "est_correct": {"bsonType": "bool"},
                            },
                        },
                    },
                },
            },
        },
    },
}


def initialiser_collection(db):
    """Crée ou met à jour la collection « quiz », sa règle de validation et ses index.

    L'opération peut être relancée sans risque (idempotente).

    Args:
        db: base MongoDB (pymongo.database.Database).
    """
    validateur = {"$jsonSchema": SCHEMA_QUIZ}
    if NOM_COLLECTION in db.list_collection_names():
        db.command("collMod", NOM_COLLECTION, validator=validateur)
    else:
        db.create_collection(NOM_COLLECTION, validator=validateur)
    collection = db[NOM_COLLECTION]
    # Liste des quiz d'un enseignant, du plus récent au plus ancien
    collection.create_index(
        [("id_utilisateur", ASCENDING), ("date_creation", DESCENDING)],
        name="proprietaire_date",
    )
    # Quiz d'une leçon (compte avant la suppression d'une leçon)
    collection.create_index([("id_lecon", ASCENDING)], name="lecon")
