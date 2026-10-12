"""En-têtes de sécurité HTTP : Content-Security-Policy (CSP) et compléments.

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

Il ajoute aussi trois en-têtes que Django n'envoie pas (signalés par le scan
OWASP ZAP) :

- Permissions-Policy : l'application n'utilise ni caméra, ni micro, ni
  localisation, ni paiement ; le navigateur les refuse à toute page du site ;
- Cross-Origin-Resource-Policy : les ressources du site ne peuvent pas être
  chargées par un autre site ;
- Cross-Origin-Embedder-Policy : la page ne charge que des ressources qui
  l'autorisent explicitement (toutes viennent du site lui-même).
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

AUTRES_ENTETES = {
    "Permissions-Policy": ", ".join(
        f"{fonction}=()"
        for fonction in (
            "camera",
            "microphone",
            "geolocation",
            "payment",
            "usb",
            "fullscreen",
        )
    ),
    "Cross-Origin-Resource-Policy": "same-origin",
    "Cross-Origin-Embedder-Policy": "require-corp",
}


class PolitiqueSecuriteContenuMiddleware:
    """Ajoute la CSP et les autres en-têtes de sécurité à chaque réponse."""

    def __init__(self, get_response):
        """Mémorise la suite de la chaîne des middlewares."""
        self.get_response = get_response

    def __call__(self, request):
        """Ajoute les en-têtes, sauf ceux que la vue a déjà fixés."""
        reponse = self.get_response(request)
        reponse.headers.setdefault("Content-Security-Policy", POLITIQUE)
        for nom, valeur in AUTRES_ENTETES.items():
            reponse.headers.setdefault(nom, valeur)
        return reponse
