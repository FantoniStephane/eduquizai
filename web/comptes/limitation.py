"""Limitation des essais de connexion (protection contre la force brute).

Chaque échec de connexion est compté dans le cache de Django, pendant 15 minutes
à partir du premier échec :
- par couple adresse e-mail + adresse IP : au-delà de 5 échecs, ce compte ne
  peut plus être essayé depuis cette IP (deviner un mot de passe) ;
- par adresse IP seule : au-delà de 20 échecs, toutes adresses confondues,
  l'IP est bloquée (robot qui essaie de nombreux comptes).

Une connexion réussie remet à zéro le compteur du compte, pas celui de l'IP :
un attaquant qui possède un compte ne peut pas effacer ses autres échecs.
Les clés du cache sont des empreintes SHA-256 : aucune adresse e-mail ni IP
n'y est stockée en clair.

Limites (déploiement) : le cache doit être partagé entre les processus du
serveur (Redis ou cache en base) et, derrière un proxy inverse, l'adresse IP
réelle doit être lue de façon sûre.
"""

import hashlib

from django.core.cache import cache

MAX_ECHECS_COMPTE = 5
MAX_ECHECS_IP = 20
DUREE_BLOCAGE = 15 * 60  # secondes
MESSAGE_BLOCAGE = "Trop de tentatives de connexion. Réessayez dans 15 minutes."


def adresse_ip(request):
    """Adresse IP du visiteur (vide si la requête est inconnue)."""
    if request is None:
        return ""
    return request.META.get("REMOTE_ADDR", "")


def _cle(*parties):
    """Clé de cache anonymisée (empreinte SHA-256 des parties)."""
    empreinte = hashlib.sha256("|".join(parties).encode()).hexdigest()
    return f"connexion-echecs:{empreinte}"


def _cles(adresse, ip):
    """Clés des deux compteurs : compte + IP, puis IP seule."""
    return _cle("compte", (adresse or "").lower(), ip), _cle("ip", ip)


def est_bloque(adresse, ip):
    """Vrai si le compte (depuis cette IP) ou l'IP a trop d'échecs récents."""
    cle_compte, cle_ip = _cles(adresse, ip)
    return (
        cache.get(cle_compte, 0) >= MAX_ECHECS_COMPTE
        or cache.get(cle_ip, 0) >= MAX_ECHECS_IP
    )


def enregistrer_echec(adresse, ip):
    """Ajoute un échec aux deux compteurs (créés pour 15 minutes au besoin)."""
    for cle in _cles(adresse, ip):
        cache.add(cle, 0, DUREE_BLOCAGE)
        try:
            cache.incr(cle)
        except ValueError:  # compteur expiré entre-temps : on repart de 1
            cache.set(cle, 1, DUREE_BLOCAGE)


def effacer_echecs(adresse, ip):
    """Remet à zéro le compteur du compte après une connexion réussie."""
    cache.delete(_cles(adresse, ip)[0])
