"""
Couche application — orchestration et logique métier du gateway.

Services :
    gateway_service.py      Proxy vers ingestion/search + filtrage par rôle
    auth_service.py         Inscription, connexion, JWT, bootstrap admin
    feedback_service.py     Retours utilisateur (👍 / 👎) sur les réponses chat
    usage_stats_service.py  Statistiques d'usage de la plateforme
    user_admin_service.py   Gestion des rôles utilisateurs (admin)
"""
