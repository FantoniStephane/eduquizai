"""En-tête de sécurité Content-Security-Policy (CSP).

La CSP indique au navigateur d'où une page a le droit de charger ses ressources.
C'est une défense en profondeur contre le XSS : même si un script réussissait à
se glisser dans une page, le navigateur refuserait de l'exécuter, car seuls les
fichiers JavaScript servis par l'application sont autorisés (aucun script en
ligne, aucun site extérieur).

Seule exception : les styles en ligne (« unsafe-inline » pour style-src), dont
l'éditeur Trix a besoin (il ajoute sa propre feuille de style dans la page).
Un style ne peut pas exécuter de code.

Django 5.2 n'a pas de réglage CSP intégré : ce petit middleware l'ajoute à
toutes les réponses. Les autres en-têtes (X-Frame-Options, X-Content-Type-Options,
Referrer-Policy, Cross-Origin-Opener-Policy) sont déjà envoyés par Django.
"""

POLITIQUE = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)


class PolitiqueSecuriteContenuMiddleware:
    """Ajoute l'en-tête Content-Security-Policy à chaque réponse."""

    def __init__(self, get_response):
        """Mémorise la suite de la chaîne des middlewares."""
        self.get_response = get_response

    def __call__(self, request):
        """Ajoute la politique, sauf si la vue en a déjà fixé une."""
        reponse = self.get_response(request)
        reponse.headers.setdefault("Content-Security-Policy", POLITIQUE)
        return reponse
