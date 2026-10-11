"""Tests des en-têtes de sécurité HTTP (CSP et en-têtes de Django)."""

from django.test import TestCase
from django.urls import reverse

from comptes.models import Utilisateur


class EntetesSecuriteTests(TestCase):
    """Chaque réponse porte les en-têtes de sécurité attendus."""

    def _csp(self, reponse):
        """Directives de la CSP, sous forme de dictionnaire."""
        directives = reponse.headers["Content-Security-Policy"].split(";")
        return {
            d.split()[0]: d.split()[1:] for d in (x.strip() for x in directives) if d
        }

    def test_csp_sur_la_page_de_connexion(self):
        """Page publique : seuls les scripts de l'application sont autorisés."""
        csp = self._csp(self.client.get(reverse("comptes:connexion")))
        self.assertEqual(csp["script-src"], ["'self'"])
        self.assertEqual(csp["object-src"], ["'none'"])
        self.assertEqual(csp["frame-ancestors"], ["'none'"])
        self.assertNotIn("'unsafe-inline'", csp["default-src"])

    def test_csp_sur_une_page_connectee_et_une_erreur_404(self):
        """La politique s'applique aussi aux pages privées et aux erreurs."""
        enseignant = Utilisateur.objects.create_user(
            "anne.durand@eduquizai.local", "Tableau-Noir-2026"
        )
        self.client.force_login(enseignant)
        for url in (reverse("lecons:creer"), "/page-inexistante/"):
            with self.subTest(url=url):
                reponse = self.client.get(url)
                self.assertEqual(self._csp(reponse)["script-src"], ["'self'"])

    def test_autres_entetes_de_django(self):
        """Clickjacking, type MIME et référent sont protégés."""
        reponse = self.client.get(reverse("comptes:connexion"))
        self.assertEqual(reponse.headers["X-Frame-Options"], "DENY")
        self.assertEqual(reponse.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(reponse.headers["Referrer-Policy"], "same-origin")
