"""Tests de l'API REST : authentification JWT et codes de réponse."""

import time
import uuid
from unittest import mock

import jwt
from django.conf import settings
from django.test import SimpleTestCase
from rest_framework.test import APIClient

from .erreurs import DelaiDepasseError, IAIndisponibleError
from .tests import LECON, TYPES, qcm, reponse_ollama
from .validation import ReponseInvalideError

URL = "/api/generer-quiz/"
DEMANDE = {"contenu": LECON, "difficulte": "moyen", "types": ["qcm"], "nombre": 3}


def fabriquer_jeton(cle=None, **modifications):
    """Fabrique un jeton comme le ferait l'application web (HS256)."""
    maintenant = int(time.time())
    contenu = {
        "token_type": "access",
        "user_id": 42,
        "jti": uuid.uuid4().hex,
        "iat": maintenant,
        "exp": maintenant + 120,
        "iss": settings.SIMPLE_JWT["ISSUER"],
        "aud": settings.SIMPLE_JWT["AUDIENCE"],
    }
    contenu.update(modifications)
    contenu = {nom: valeur for nom, valeur in contenu.items() if valeur is not None}
    return jwt.encode(
        contenu, cle or settings.SIMPLE_JWT["SIGNING_KEY"], algorithm="HS256"
    )


class AuthentificationTests(SimpleTestCase):
    """Sans jeton valide, l'API refuse tout et n'appelle jamais l'IA."""

    def appeler(self, jeton=None):
        """Appelle l'API avec le jeton donné (aucun en-tête si None)."""
        client = APIClient()
        if jeton is not None:
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {jeton}")
        return client.post(URL, DEMANDE, format="json")

    @mock.patch("generation.views.generer_quiz")
    def test_jetons_refuses(self, generer):
        """Absent, illisible, expiré, mal signé, mal destiné : 401."""
        cas = {
            "aucun jeton": None,
            "jeton illisible": "n-importe-quoi",
            "jeton expiré": fabriquer_jeton(exp=int(time.time()) - 10),
            "mauvais secret": fabriquer_jeton(cle="x" * 48),
            "mauvais destinataire": fabriquer_jeton(aud="autre-service"),
            "mauvais émetteur": fabriquer_jeton(iss="autre-emetteur"),
            "sans destinataire": fabriquer_jeton(aud=None),
            "sans identifiant": fabriquer_jeton(user_id=None),
            "jeton de rafraîchissement": fabriquer_jeton(token_type="refresh"),
        }
        for nom, jeton in cas.items():
            with self.subTest(nom):
                self.assertEqual(self.appeler(jeton).status_code, 401)
        generer.assert_not_called()

    def test_algorithme_none_refuse(self):
        """Un jeton non signé (alg « none ») est refusé."""
        jeton = jwt.encode(
            {"token_type": "access", "user_id": 1, "exp": int(time.time()) + 60},
            None,
            algorithm="none",
        )
        self.assertEqual(self.appeler(jeton).status_code, 401)

    def test_methode_get_refusee(self):
        """Seul POST est accepté."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {fabriquer_jeton()}")
        self.assertEqual(client.get(URL).status_code, 405)


@mock.patch("generation.ollama.requests.post")
class GenererQuizApiTests(SimpleTestCase):
    """Appels authentifiés de l'API de génération."""

    def setUp(self):
        """Prépare un client muni d'un jeton valide."""
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {fabriquer_jeton()}")

    def test_generation_reussie(self, post):
        """Demande valide : 200 et questions au format de l'application."""
        post.return_value = reponse_ollama([qcm(), qcm(1), qcm(2)])
        reponse = self.client.post(URL, DEMANDE, format="json")
        self.assertEqual(reponse.status_code, 200)
        questions = reponse.json()["questions"]
        self.assertEqual(len(questions), 3)
        self.assertEqual(questions[0]["choix"][0]["est_correct"], True)

    def test_parametres_invalides(self, post):
        """Paramètre hors limites, manquant ou corps inattendu : 400, sans appel IA."""
        cas = {
            "nombre trop grand": {**DEMANDE, "nombre": 99},
            "difficulté inconnue": {**DEMANDE, "difficulte": "impossible"},
            "type inconnu": {**DEMANDE, "types": ["piege"]},
            "contenu vide": {**DEMANDE, "contenu": "  "},
            "contenu absent": {"difficulte": "moyen", "types": TYPES, "nombre": 3},
            "corps en liste": [1, 2, 3],
        }
        for nom, corps in cas.items():
            with self.subTest(nom):
                reponse = self.client.post(URL, corps, format="json")
                self.assertEqual(reponse.status_code, 400)
        post.assert_not_called()

    @mock.patch("generation.views.generer_quiz")
    def test_erreurs_de_l_ia(self, generer, post):
        """Chaque problème d'IA a son code, avec un message sans détail interne."""
        cas = [
            (IAIndisponibleError("http://ollama:11434 injoignable"), 503),
            (DelaiDepasseError("60 s"), 504),
            (ReponseInvalideError("Question 2 : choix manquants"), 502),
        ]
        for erreur, code in cas:
            with self.subTest(code=code):
                generer.side_effect = erreur
                # Le détail technique va dans les journaux, pas dans la réponse
                with self.assertLogs("generation.views", level="WARNING"):
                    reponse = self.client.post(URL, DEMANDE, format="json")
                self.assertEqual(reponse.status_code, code)
                self.assertNotIn(str(erreur), reponse.content.decode())
