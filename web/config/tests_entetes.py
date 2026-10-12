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

    def test_entetes_ajoutes_apres_le_scan_zap(self):
        """Fonctions du navigateur interdites, ressources réservées au site."""
        reponse = self.client.get(reverse("comptes:connexion"))
        politique = reponse.headers["Permissions-Policy"]
        for fonction in ("camera", "microphone", "geolocation"):
            with self.subTest(fonction=fonction):
                self.assertIn(f"{fonction}=()", politique)
        entetes = reponse.headers
        self.assertEqual(entetes["Cross-Origin-Resource-Policy"], "same-origin")
        self.assertEqual(entetes["Cross-Origin-Embedder-Policy"], "require-corp")

    def test_cookie_csrf_illisible_par_javascript(self):
        """Le cookie CSRF porte l'attribut HttpOnly."""
        reponse = self.client.get(reverse("comptes:connexion"))
        self.assertTrue(reponse.cookies["csrftoken"]["httponly"])
