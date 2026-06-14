# config.py — Copie ce fichier en "config.py" et remplis tes clés
# config.py est dans .gitignore → tes clés ne seront PAS poussées sur GitHub

# ── Adzuna (France + Espagne)
# Inscription gratuite : https://developer.adzuna.com/
ADZUNA_APP_ID  = 'TON_APP_ID'
ADZUNA_APP_KEY = 'TON_APP_KEY'

# ── Jooble (France + Espagne)
# Formulaire email : https://jooble.org/api/index (clé reçue par email en quelques minutes)
JOOBLE_KEY = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'

# ── France Travail (Pôle Emploi) — SOURCE PRINCIPALE IDF
# 1. Crée un compte sur https://pole-emploi.io
# 2. Créer une application
# 3. Souscrire à "Offres d'emploi v2"
# 4. Copier client_id et client_secret ci-dessous
FT_CLIENT_ID     = 'TON_CLIENT_ID'
FT_CLIENT_SECRET = 'TON_CLIENT_SECRET'

# ── Git Push automatique
# True  = pousse automatiquement sur GitHub après chaque scrape
# False = sauvegarde les JSON localement sans pousser
GITHUB_AUTO_PUSH = True
