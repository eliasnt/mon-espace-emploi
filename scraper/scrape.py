"""
Scraper local — Mon Espace Emploi
===================================
Lance ce script manuellement ou programme-le avec le Planificateur de tâches Windows.
Il récupère les offres depuis plusieurs sources, filtre IDF, puis met à jour
les fichiers JSON dans ../data/ et pousse sur GitHub.

Usage:
    python scrape.py           # Scrape tout + push GitHub
    python scrape.py --no-push # Scrape sans pousser
    python scrape.py --test    # Test IDF filter uniquement
"""

import sys
import os
import json
import re
import time
import subprocess
import feedparser
import requests
from datetime import datetime, timezone
from pathlib import Path

# ══════════════════════════════════════════════════════════════
# CONFIG — Remplis tes clés ici ou dans config.py
# ══════════════════════════════════════════════════════════════

try:
    from config import (
        ADZUNA_APP_ID, ADZUNA_APP_KEY,
        JOOBLE_KEY,
        FT_CLIENT_ID, FT_CLIENT_SECRET,
        GITHUB_AUTO_PUSH,
    )
except ImportError:
    ADZUNA_APP_ID    = os.getenv('ADZUNA_APP_ID', '')
    ADZUNA_APP_KEY   = os.getenv('ADZUNA_APP_KEY', '')
    JOOBLE_KEY       = os.getenv('JOOBLE_KEY', '')
    FT_CLIENT_ID     = os.getenv('FT_CLIENT_ID', '')       # France Travail
    FT_CLIENT_SECRET = os.getenv('FT_CLIENT_SECRET', '')   # France Travail
    GITHUB_AUTO_PUSH = True

DATA_DIR = Path(__file__).parent.parent / 'data'
DATA_DIR.mkdir(exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'fr-FR,fr;q=0.9',
}

# ══════════════════════════════════════════════════════════════
# FILTRAGE IDF — VÉRIFICATION STRICTE
# ══════════════════════════════════════════════════════════════

# Codes postaux commençant par ces 2 chiffres = Île-de-France garanti
IDF_CP_PREFIXES = {'75', '77', '78', '91', '92', '93', '94', '95'}

# Noms de départements IDF (en minuscules)
IDF_DEPT_NAMES = {
    'paris', 'seine-et-marne', 'yvelines', 'essonne',
    'hauts-de-seine', 'seine-saint-denis', 'val-de-marne', "val-d'oise",
    "val d'oise", 'val d oise', 'île-de-france', 'ile-de-france',
    'idf', 'grand paris', 'région parisienne', 'banlieue parisienne',
}

# Villes IDF notables (en minuscules, sans accents pour matching souple)
IDF_CITIES = {
    'paris', 'boulogne-billancourt', 'boulogne', 'vincennes', 'montreuil',
    'saint-denis', 'nanterre', 'creteil', 'créteil', 'versailles', 'bobigny',
    'evry', 'évry', 'cergy', 'argenteuil', 'colombes', 'asnieres', 'asnières',
    'vitry-sur-seine', 'vitry', 'champigny', 'rueil-malmaison', 'rueil',
    'courbevoie', 'aulnay-sous-bois', 'aulnay', 'drancy', 'pantin', 'neuilly',
    'levallois', 'issy', 'clamart', 'antony', 'epinay', 'épinay', 'noisy',
    'chelles', 'meaux', 'melun', 'pontoise', 'saint-germain-en-laye',
    'saint-germain', 'corbeil', 'palaiseau', 'massy', 'la defense',
    'bagneux', 'montrouge', 'ivry-sur-seine', 'ivry', 'alfortville', 'choisy',
    'orly', 'villeneuve', 'bagnolet', 'romainville', 'sarcelles', 'trappes',
    'poissy', 'sartrouville', 'conflans', 'maisons-alfort', 'fontenay',
    'saint-maur', 'rosny', 'bondy', 'aubervilliers', 'gennevilliers',
    'meudon', 'chatou', 'houilles', 'chatillon', 'montfermeil', 'les lilas',
    'le kremlin-bicetre', 'charenton', 'nogent-sur-marne', 'joinville',
    'vincennes', 'montrogue', 'vanves', 'malakoff', 'chatenay-malabry',
    'velizy', 'vélizy', 'gif-sur-yvette', 'saclay', 'orsay', 'longjumeau',
    'rungis', 'thiais', 'fresnes', 'villejuif', 'gentilly', 'cachan',
    'arcueil', 'bourg-la-reine', 'sceaux', 'paray-vieille-poste',
    'saint-ouen', 'saint-ouen-sur-seine', 'clichy', 'levallois-perret',
    'puteaux', 'suresnes', 'la garenne-colombes', 'bois-colombes',
    'colombes', 'asnieres-sur-seine', 'chatou', 'le pecq', 'saint-cloud',
    'garches', 'marnes-la-coquette', 'vaucresson', 'ville-d-avray',
    'sevres', 'sèvres', 'meudon', 'chaville', 'viroflay', 'le chesnay',
    'la celle-saint-cloud', 'les clayes', 'plaisir', 'maurepas',
    'saint-quentin-en-yvelines', 'montigny', 'guyancourt', 'elancourt',
    'acheres', 'andrezieux', 'montlhery', 'longjumeau',
}

# Abréviations d'États américains (pour rejeter "Paris, TX" etc.)
US_STATE_ABBREVS = {
    'al','ak','az','ar','ca','co','ct','de','fl','ga','hi','id','il','in',
    'ia','ks','ky','la','me','md','ma','mi','mn','ms','mo','mt','ne','nv',
    'nh','nj','nm','ny','nc','nd','oh','ok','or','pa','ri','sc','sd','tn',
    'tx','ut','vt','va','wa','wv','wi','wy','dc',
}

# Regex : "Paris, TX" ou "Paris, Tennessee" → hors France
RE_US_PARIS = re.compile(r'paris,?\s+([a-z]{2,})$', re.IGNORECASE)

# Mots-clés étrangers à rejeter dans la localisation
FOREIGN_MARKERS = [
    'united states', 'united kingdom', 'usa', 'u.s.a', 'canada', 'ontario',
    'england', 'australia', 'deutschland', 'españa', 'nederland',
    'belgique', 'suisse', 'schweiz', 'italia', 'polska', 'brasil',
    'texas', 'tennessee', 'california', 'florida', 'new york', 'georgia',
    'louisiana', 'indiana', 'virginia', 'kentucky', 'ohio', 'michigan',
    'colorado', 'arizona', 'nevada', 'minnesota', 'illinois', 'wisconsin',
]


def clean_loc(s: str) -> str:
    """Lowercase, strip accents pour matching souple."""
    s = s.lower().strip()
    replacements = {'é': 'e', 'è': 'e', 'ê': 'e', 'à': 'a', 'â': 'a',
                    'î': 'i', 'ï': 'i', 'ô': 'o', 'ù': 'u', 'û': 'u', 'ç': 'c'}
    for orig, rep in replacements.items():
        s = s.replace(orig, rep)
    return s


def is_idf(location: str, postal_code: str = '', country: str = 'FR') -> bool:
    """
    Retourne True si l'offre est bien en Île-de-France.

    Méthodes de vérification (par ordre de fiabilité) :
    1. Code postal → département IDF
    2. Numéro de département dans la localisation
    3. Nom de département IDF dans la localisation
    4. Ville IDF connue dans la localisation
    5. Rejet des faux positifs (Paris TX, Paris TN, etc.)
    """
    if country and country.upper() not in ('FR', 'FRANCE', ''):
        return False

    # 1. Code postal — méthode la plus fiable
    cp = str(postal_code).strip().replace(' ', '')
    if cp and len(cp) >= 2:
        if cp[:2] in IDF_CP_PREFIXES:
            return True
        # Format "75001" ou "750" → Paris
        if cp.startswith('750') or cp.startswith('751') or cp.startswith('752'):
            return True

    loc = location.strip()
    if not loc:
        return False

    loc_lower = loc.lower()

    # 2. Rejeter pays étrangers
    if any(k in loc_lower for k in FOREIGN_MARKERS):
        return False

    # 3. Rejeter "Paris, XX" où XX est une abréviation d'État US
    m = RE_US_PARIS.search(loc_lower)
    if m:
        suffix = m.group(1).lower().strip('.,')
        if suffix in US_STATE_ABBREVS:
            return False
        # Nom d'État US en toutes lettres
        us_states_full = {
            'texas', 'tennessee', 'california', 'florida', 'georgia',
            'ohio', 'indiana', 'virginia', 'kentucky', 'michigan',
            'illinois', 'wisconsin', 'louisiana', 'arkansas', 'idaho',
        }
        if suffix in us_states_full:
            return False

    # 4. Numéro de département IDF dans la chaîne
    for code in IDF_CP_PREFIXES:
        patterns = [f'({code})', f' {code})', f'[{code}]', f'- {code}',
                    f', {code}', f'/{code}', f'{code}000', f'{code}xxx']
        if any(p.lower() in loc_lower for p in patterns):
            return True
        # "75" ou "93" en début ou entre parenthèses
        if re.search(rf'\b{code}\b', loc_lower):
            return True

    # 5. Nom de département IDF
    if any(dept in loc_lower for dept in IDF_DEPT_NAMES):
        return True

    # 6. Ville IDF connue (matching souple sans accents)
    loc_clean = clean_loc(loc)
    if any(city in loc_clean for city in IDF_CITIES):
        return True

    return False


# ══════════════════════════════════════════════════════════════
# UTILITAIRES
# ══════════════════════════════════════════════════════════════

def dedup(jobs: list) -> list:
    """Supprime les doublons par URL."""
    seen = set()
    out = []
    for j in jobs:
        key = j.get('url', '') or j.get('id', '')
        if key and key not in seen:
            seen.add(key)
            out.append(j)
    return out


def clean_desc(html: str, maxlen: int = 500) -> str:
    """Retire les balises HTML et tronque."""
    text = re.sub(r'<[^>]+>', ' ', html or '')
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:maxlen]


def job_id(prefix: str, unique: str) -> str:
    safe = re.sub(r'[^a-z0-9]', '', unique.lower())[:20]
    return f"{prefix}-{safe or str(int(time.time()))}"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')


# ══════════════════════════════════════════════════════════════
# SOURCE 1 : FRANCE TRAVAIL (PÔLE EMPLOI) ← MEILLEURE SOURCE IDF
# ══════════════════════════════════════════════════════════════
# Inscription gratuite : https://pole-emploi.io
# Créer une application → souscrire "Offres d'emploi v2" → récupérer client_id / client_secret

def _ft_token() -> str:
    """OAuth2 client_credentials pour France Travail."""
    if not FT_CLIENT_ID or not FT_CLIENT_SECRET:
        return ''
    try:
        r = requests.post(
            'https://entreprise.francetravail.fr/connexion/oauth2/access_token',
            params={'realm': '/partenaire'},
            data={
                'grant_type': 'client_credentials',
                'client_id': FT_CLIENT_ID,
                'client_secret': FT_CLIENT_SECRET,
                'scope': 'api_offresdemploiv2 o2dsoffre',
            },
            timeout=10,
        )
        return r.json().get('access_token', '')
    except Exception as e:
        print(f"  [FT] Erreur token : {e}")
        return ''


def fetch_france_travail() -> list:
    """Offres IDF depuis l'API officielle France Travail."""
    if not FT_CLIENT_ID or not FT_CLIENT_SECRET:
        print("  [FT] Clés manquantes — ignoré (voir config.py)")
        return []

    token = _ft_token()
    if not token:
        print("  [FT] Impossible d'obtenir le token")
        return []

    # Codes département IDF passés directement à l'API → 100% IDF garanti
    IDF_DEPTS = '75,77,78,91,92,93,94,95'
    queries = [
        'animateur éducateur jeunesse',
        'assistant BAFA périscolaire animation',
        'accompagnant scolaire AESH',
        'assistant ressources humaines RH recrutement',
        'chargé clientèle téléconseiller relation client',
        'réceptionniste hôtel hébergement',
        'agent accueil hôtellerie',
        'débutant sans expérience formation',
        'gouvernante chambre hôtel',
        'secrétaire administratif accueil',
    ]
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    results = []
    seen_ids = set()

    for q in queries:
        try:
            r = requests.get(
                'https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search',
                params={
                    'motsCles': q,
                    'departement': IDF_DEPTS,
                    'range': '0-49',
                    'tri': 1,  # date décroissante
                },
                headers=headers,
                timeout=12,
            )
            if r.status_code != 200:
                continue
            data = r.json()
            for o in data.get('resultats', []):
                oid = o.get('id', '')
                if not oid or oid in seen_ids:
                    continue
                seen_ids.add(oid)
                lieu = o.get('lieuTravail', {})
                cp = lieu.get('codePostal', '')
                loc = lieu.get('libelle', '')
                # Double-check IDF even though API already filters by departement
                if cp and cp[:2] not in IDF_CP_PREFIXES:
                    continue
                results.append({
                    'id': f'ft-{oid}',
                    'source': 'francetravail',
                    'title': o.get('intitule', ''),
                    'company': o.get('entreprise', {}).get('nom', ''),
                    'location': f"{loc} ({cp[:2] if cp else ''})",
                    'postal_code': cp,
                    'contract': o.get('typeContratLibelle', ''),
                    'date': o.get('dateCreation', ''),
                    'url': o.get('origineOffre', {}).get('urlOrigine')
                           or f"https://candidat.francetravail.fr/offres/recherche/detail/{oid}",
                    'desc': clean_desc(o.get('description', '')),
                    '_idf_verified': True,
                })
            time.sleep(0.3)  # courtoisie rate-limit
        except Exception as e:
            print(f"  [FT] Erreur pour '{q}' : {e}")

    print(f"  [FT] {len(results)} offres IDF récupérées")
    return results


# ══════════════════════════════════════════════════════════════
# SOURCE 2 : ADZUNA FRANCE
# ══════════════════════════════════════════════════════════════

def fetch_adzuna_fr() -> list:
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        print("  [Adzuna FR] Clés manquantes — ignoré")
        return []

    queries = [
        'animateur éducateur BAFA jeunesse',
        'assistant éducatif AESH accompagnant scolaire',
        'assistant ressources humaines RH',
        'chargé recrutement administration personnel',
        'chargé clientèle téléconseiller accueil',
        'réceptionniste hôtel hébergement',
        'gouvernante femme chambre hôtel',
        'débutant sans expérience formation assurée',
        'conseiller commercial relation client',
        'secrétaire administratif bureau',
    ]
    results = []
    seen = set()

    for q in queries:
        for page in [1, 2]:
            try:
                r = requests.get(
                    f'https://api.adzuna.com/v1/api/jobs/fr/search/{page}',
                    params={
                        'app_id': ADZUNA_APP_ID,
                        'app_key': ADZUNA_APP_KEY,
                        'results_per_page': 50,
                        'what': q,
                        'where': 'Île-de-France',
                        'content-type': 'application/json',
                    },
                    timeout=12,
                )
                data = r.json()
                for j in data.get('results', []):
                    jid = j.get('id', '')
                    if not jid or jid in seen:
                        continue
                    seen.add(jid)
                    loc = j.get('location', {}).get('display_name', '')
                    if not is_idf(loc):
                        continue
                    results.append({
                        'id': f'az-{jid}',
                        'source': 'adzuna',
                        'title': j.get('title', ''),
                        'company': j.get('company', {}).get('display_name', ''),
                        'location': loc,
                        'postal_code': '',
                        'contract': j.get('contract_type', ''),
                        'date': j.get('created', ''),
                        'url': j.get('redirect_url', ''),
                        'desc': clean_desc(j.get('description', '')),
                        '_idf_verified': True,
                    })
                time.sleep(0.2)
            except Exception as e:
                print(f"  [Adzuna FR] Erreur page {page} pour '{q}' : {e}")

    print(f"  [Adzuna FR] {len(results)} offres IDF")
    return results


# ══════════════════════════════════════════════════════════════
# SOURCE 3 : JOOBLE FRANCE
# ══════════════════════════════════════════════════════════════

def fetch_jooble_fr() -> list:
    if not JOOBLE_KEY:
        print("  [Jooble FR] Clé manquante — ignoré")
        return []

    queries = [
        ('animateur éducateur BAFA', 'Île-de-France'),
        ('assistant RH recrutement', 'Paris'),
        ('chargé clientèle téléconseiller', 'Île-de-France'),
        ('réceptionniste hôtel', 'Paris'),
        ('débutant sans expérience', 'Île-de-France'),
        ('accompagnant scolaire AESH', 'Île-de-France'),
    ]
    results = []
    seen = set()

    for keywords, location in queries:
        try:
            r = requests.post(
                f'https://jooble.org/api/{JOOBLE_KEY}',
                json={'keywords': keywords, 'location': location, 'resultonpage': 25},
                headers={'Content-Type': 'application/json'},
                timeout=12,
            )
            for j in r.json().get('jobs', []):
                jid = str(j.get('id', ''))
                if not jid or jid in seen:
                    continue
                seen.add(jid)
                loc = j.get('location', '')
                if not is_idf(loc):
                    continue
                results.append({
                    'id': f'jb-{jid}',
                    'source': 'jooble',
                    'title': j.get('title', ''),
                    'company': j.get('company', ''),
                    'location': loc,
                    'postal_code': '',
                    'contract': j.get('type', ''),
                    'date': j.get('updated', ''),
                    'url': j.get('link', ''),
                    'desc': clean_desc(j.get('snippet', '')),
                    '_idf_verified': True,
                })
            time.sleep(0.3)
        except Exception as e:
            print(f"  [Jooble FR] Erreur pour '{keywords}' : {e}")

    print(f"  [Jooble FR] {len(results)} offres IDF")
    return results


# ══════════════════════════════════════════════════════════════
# SOURCE 4 : INDEED RSS FRANCE
# ══════════════════════════════════════════════════════════════

def fetch_indeed_rss_fr() -> list:
    queries = [
        ('animateur+educateur+BAFA',          'Ile-de-France'),
        ('assistant+RH+recrutement',           'Paris'),
        ('chargé+clientèle+téléconseiller',    'Ile-de-France'),
        ('réceptionniste+hôtel',               'Paris'),
        ('débutant+sans+expérience',           'Ile-de-France'),
        ('accompagnant+scolaire',              'Ile-de-France'),
        ('animation+periscolaire',             'Ile-de-France'),
        ('agent+accueil+hotellerie',           'Paris'),
    ]
    results = []
    seen = set()

    for q, loc in queries:
        url = f'https://fr.indeed.com/rss?q={q}&l={requests.utils.quote(loc)}&sort=date'
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                link = entry.get('link', '')
                if not link or link in seen:
                    continue
                location = entry.get('location', '')
                # Indeed FR RSS → les offres sont déjà filtrées par la query "l=",
                # mais on vérifie quand même pour sécuriser contre faux positifs
                if location and not is_idf(location):
                    continue
                seen.add(link)
                results.append({
                    'id': job_id('ind', link),
                    'source': 'indeed',
                    'title': entry.get('title', ''),
                    'company': entry.get('author', ''),
                    'location': location or 'Île-de-France',
                    'postal_code': '',
                    'contract': '',
                    'date': entry.get('published', ''),
                    'url': link,
                    'desc': clean_desc(entry.get('summary', '')),
                    '_idf_verified': bool(location),
                })
            time.sleep(0.5)
        except Exception as e:
            print(f"  [Indeed RSS FR] Erreur pour '{q}' : {e}")

    print(f"  [Indeed RSS FR] {len(results)} offres")
    return results


# ══════════════════════════════════════════════════════════════
# SOURCE 5 : JOBTOME RSS FRANCE
# ══════════════════════════════════════════════════════════════

def fetch_jobtome_fr() -> list:
    slug = 'paris'  # Jobtome utilise un slug de ville
    queries = [
        'animateur', 'educateur', 'assistant-rh', 'conseiller-clientele',
        'receptionniste', 'hotellerie', 'debutant', 'accueil',
    ]
    results = []
    seen = set()

    for q in queries:
        url = f'https://fr.jobtome.com/rss.xml?q={q}&l={slug}'
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                link = entry.get('link', '')
                if not link or link in seen:
                    continue
                loc = entry.get('location', 'Paris')
                if not is_idf(loc, country='FR'):
                    continue
                seen.add(link)
                results.append({
                    'id': job_id('jtfr', link),
                    'source': 'jobtome',
                    'title': entry.get('title', ''),
                    'company': '',
                    'location': loc or 'Paris',
                    'postal_code': '',
                    'contract': '',
                    'date': entry.get('published', ''),
                    'url': link,
                    'desc': clean_desc(entry.get('summary', '')),
                    '_idf_verified': True,
                })
            time.sleep(0.4)
        except Exception as e:
            print(f"  [Jobtome FR] Erreur pour '{q}' : {e}")

    print(f"  [Jobtome FR] {len(results)} offres")
    return results


# ══════════════════════════════════════════════════════════════
# SOURCES ESPAGNE — AU PAIR
# ══════════════════════════════════════════════════════════════

def fetch_adzuna_es() -> list:
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        print("  [Adzuna ES] Clés manquantes — ignoré")
        return []

    queries = [
        ('niñera',    'Barcelona',        'Barcelona'),
        ('au pair',   'Barcelona',        'Barcelona'),
        ('canguro',   'Barcelona',        'Barcelona'),
        ('babysitter','Barcelona',        'Barcelona'),
        ('cuidadora', 'Barcelona',        'Barcelona'),
        ('nanny',     'Barcelona',        'Barcelona'),
        ('niñera',    'Palma',            'Palma de Mallorca'),
        ('au pair',   'Palma',            'Palma de Mallorca'),
        ('canguro',   'Palma',            'Palma de Mallorca'),
        ('nanny',     'Palma',            'Palma de Mallorca'),
        ('niñera',    'Mallorca',         'Palma de Mallorca'),
        ('cuidadora', 'Palma',            'Palma de Mallorca'),
        ('niñera',    'Madrid',           'Madrid'),
        ('au pair',   'Madrid',           'Madrid'),
        ('au pair',   'Valencia',         'Valencia'),
        ('au pair',   'Ibiza',            'Ibiza'),
    ]
    results = []
    seen = set()

    for what, where, city in queries:
        try:
            r = requests.get(
                'https://api.adzuna.com/v1/api/jobs/es/search/1',
                params={
                    'app_id': ADZUNA_APP_ID,
                    'app_key': ADZUNA_APP_KEY,
                    'results_per_page': 20,
                    'what': what,
                    'where': where,
                    'content-type': 'application/json',
                },
                timeout=12,
            )
            for j in r.json().get('results', []):
                jid = j.get('id', '')
                if not jid or jid in seen:
                    continue
                seen.add(jid)
                results.append({
                    'id': f'azes-{jid}',
                    'source': 'adzuna_es',
                    '_sourceCity': city,
                    'title': j.get('title', ''),
                    'company': j.get('company', {}).get('display_name', '') or "Famille d'accueil",
                    'location': j.get('location', {}).get('display_name', city),
                    'contract': 'Au Pair',
                    'date': j.get('created', ''),
                    'url': j.get('redirect_url', ''),
                    'desc': clean_desc(j.get('description', '')),
                })
            time.sleep(0.2)
        except Exception as e:
            print(f"  [Adzuna ES] Erreur pour '{what}' à {where} : {e}")

    print(f"  [Adzuna ES] {len(results)} offres Au Pair")
    return results


def fetch_jooble_es() -> list:
    if not JOOBLE_KEY:
        print("  [Jooble ES] Clé manquante — ignoré")
        return []

    queries = [
        ('au pair niñera',    'Barcelona',         'Barcelona'),
        ('canguro babysitter','Barcelona',          'Barcelona'),
        ('au pair nanny',     'Palma de Mallorca', 'Palma de Mallorca'),
        ('cuidadora niños',   'Palma',             'Palma de Mallorca'),
        ('au pair',           'Madrid',            'Madrid'),
    ]
    results = []
    seen = set()

    for keywords, location, city in queries:
        try:
            r = requests.post(
                f'https://jooble.org/api/{JOOBLE_KEY}',
                json={'keywords': keywords, 'location': location, 'resultonpage': 20},
                headers={'Content-Type': 'application/json'},
                timeout=12,
            )
            for j in r.json().get('jobs', []):
                jid = str(j.get('id', ''))
                if not jid or jid in seen:
                    continue
                seen.add(jid)
                results.append({
                    'id': f'jbes-{jid}',
                    'source': 'jooble',
                    '_sourceCity': city,
                    'title': j.get('title', ''),
                    'company': j.get('company', '') or "Famille d'accueil",
                    'location': j.get('location', city),
                    'contract': 'Au Pair',
                    'date': j.get('updated', ''),
                    'url': j.get('link', ''),
                    'desc': clean_desc(j.get('snippet', '')),
                })
            time.sleep(0.3)
        except Exception as e:
            print(f"  [Jooble ES] Erreur pour '{keywords}' : {e}")

    print(f"  [Jooble ES] {len(results)} offres Au Pair")
    return results


def fetch_indeed_rss_es() -> list:
    queries = [
        ('au+pair+nanny',      'Barcelona',         'Barcelona'),
        ('au+pair+nanny',      'Palma+de+Mallorca', 'Palma de Mallorca'),
        ('canguro+babysitter', 'Barcelona',         'Barcelona'),
        ('cuidadora+ninos',    'Palma',             'Palma de Mallorca'),
        ('au+pair',            'Madrid',            'Madrid'),
        ('au+pair',            'Valencia',          'Valencia'),
        ('au+pair',            'Ibiza',             'Ibiza'),
        ('ninera',             'Barcelona',         'Barcelona'),
        ('ninera',             'Palma+de+Mallorca', 'Palma de Mallorca'),
    ]
    results = []
    seen = set()

    for q, loc, city in queries:
        url = f'https://es.indeed.com/rss?q={q}&l={loc}&sort=date'
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                link = entry.get('link', '')
                if not link or link in seen:
                    continue
                seen.add(link)
                results.append({
                    'id': job_id('ines', link),
                    'source': 'indeed',
                    '_sourceCity': city,
                    'title': entry.get('title', ''),
                    'company': entry.get('author', '') or "Famille d'accueil",
                    'location': entry.get('location', city),
                    'contract': 'Au Pair',
                    'date': entry.get('published', ''),
                    'url': link,
                    'desc': clean_desc(entry.get('summary', '')),
                })
            time.sleep(0.5)
        except Exception as e:
            print(f"  [Indeed RSS ES] Erreur pour '{q}' à {loc} : {e}")

    print(f"  [Indeed RSS ES] {len(results)} offres Au Pair")
    return results


def fetch_infojobs_rss() -> list:
    """InfoJobs — 1er site d'emploi espagnol. Province: 8=BCN, 7=Balears, 28=Madrid."""
    searches = [
        ('au+pair+ni%C3%B1era', 8,  'Barcelona'),
        ('canguro+au+pair',     8,  'Barcelona'),
        ('au+pair+ni%C3%B1era', 7,  'Palma de Mallorca'),
        ('canguro+cuidadora',   7,  'Palma de Mallorca'),
        ('au+pair',             28, 'Madrid'),
    ]
    results = []
    seen = set()

    for kw, province, city in searches:
        url = f'https://www.infojobs.net/rss/ofertas.xhtml?keyword={kw}&province={province}'
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                link = entry.get('link', '')
                if not link or link in seen:
                    continue
                seen.add(link)
                results.append({
                    'id': job_id('infojs', link),
                    'source': 'infojobs',
                    '_sourceCity': city,
                    'title': entry.get('title', ''),
                    'company': entry.get('author', '') or "Famille d'accueil",
                    'location': city,
                    'contract': 'Au Pair',
                    'date': entry.get('published', ''),
                    'url': link,
                    'desc': clean_desc(entry.get('summary', '')),
                })
            time.sleep(0.5)
        except Exception as e:
            print(f"  [InfoJobs] Erreur pour province {province} : {e}")

    print(f"  [InfoJobs] {len(results)} offres Au Pair")
    return results


def fetch_jobtome_es() -> list:
    queries_cities = [
        ('au-pair',           'barcelona',          'Barcelona'),
        ('au-pair',           'palma-de-mallorca',  'Palma de Mallorca'),
        ('ninera-canguro',    'barcelona',          'Barcelona'),
        ('cuidadora-ninos',   'palma',              'Palma de Mallorca'),
        ('au-pair',           'madrid',             'Madrid'),
        ('nanny-babysitter',  'barcelona',          'Barcelona'),
    ]
    results = []
    seen = set()

    for q, loc, city in queries_cities:
        url = f'https://es.jobtome.com/rss.xml?q={q}&l={loc}'
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                link = entry.get('link', '')
                if not link or link in seen:
                    continue
                seen.add(link)
                results.append({
                    'id': job_id('jtme', link),
                    'source': 'jobtome',
                    '_sourceCity': city,
                    'title': entry.get('title', ''),
                    'company': "Famille d'accueil",
                    'location': city,
                    'contract': 'Au Pair',
                    'date': entry.get('published', ''),
                    'url': link,
                    'desc': clean_desc(entry.get('summary', '')),
                })
            time.sleep(0.4)
        except Exception as e:
            print(f"  [Jobtome ES] Erreur pour '{q}' : {e}")

    print(f"  [Jobtome ES] {len(results)} offres Au Pair")
    return results


# ══════════════════════════════════════════════════════════════
# SAVE JSON + GIT PUSH
# ══════════════════════════════════════════════════════════════

def save_json(path: Path, data) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Sauvegardé : {path} ({len(data)} entrées)")


def git_push(message: str) -> bool:
    """Commit + push le dossier data/ vers GitHub."""
    repo_root = Path(__file__).parent.parent
    try:
        subprocess.run(['git', '-C', str(repo_root), 'add', 'data/'], check=True)
        result = subprocess.run(
            ['git', '-C', str(repo_root), 'diff', '--cached', '--quiet'],
            capture_output=True,
        )
        if result.returncode == 0:
            print("  Aucun changement à pousser.")
            return True
        subprocess.run(
            ['git', '-C', str(repo_root), 'commit', '-m', message],
            check=True,
        )
        subprocess.run(
            ['git', '-C', str(repo_root), 'push'],
            check=True,
        )
        print("  ✅ Poussé sur GitHub avec succès.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Erreur git push : {e}")
        return False


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def run(push: bool = True) -> None:
    start = time.time()
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    print(f"\n{'='*55}")
    print(f"  MON ESPACE EMPLOI — Scrape du {ts}")
    print(f"{'='*55}")

    # ── OFFRES FRANCE IDF ──
    print("\n📍 OFFRES FRANCE (Île-de-France)")
    ft_jobs   = fetch_france_travail()
    az_jobs   = fetch_adzuna_fr()
    jb_jobs   = fetch_jooble_fr()
    ind_jobs  = fetch_indeed_rss_fr()
    jtfr_jobs = fetch_jobtome_fr()

    france_jobs = dedup(ft_jobs + az_jobs + jb_jobs + ind_jobs + jtfr_jobs)
    print(f"\n  → {len(france_jobs)} offres IDF au total")

    # ── OFFRES AU PAIR ESPAGNE ──
    print("\n🇪🇸 OFFRES AU PAIR ESPAGNE")
    az_es    = fetch_adzuna_es()
    jb_es    = fetch_jooble_es()
    ind_es   = fetch_indeed_rss_es()
    infojs   = fetch_infojobs_rss()
    jtme_es  = fetch_jobtome_es()

    aupair_jobs = dedup(az_es + jb_es + ind_es + infojs + jtme_es)
    print(f"\n  → {len(aupair_jobs)} offres Au Pair au total")

    # ── STATS PAR SOURCE ──
    def count_src(jobs, src):
        return sum(1 for j in jobs if j.get('source') == src)

    def count_city(jobs, city):
        patterns = {
            'barcelona': ['barcelona', 'barcelone'],
            'palma':     ['palma', 'mallorca', 'balear'],
            'madrid':    ['madrid'],
        }
        pats = patterns.get(city, [city])
        return sum(1 for j in jobs
                   if any(p in (j.get('_sourceCity','') + j.get('location','')).lower()
                          for p in pats))

    meta = {
        'last_update': now_iso(),
        'france': {
            'total': len(france_jobs),
            'by_source': {
                'francetravail': count_src(france_jobs, 'francetravail'),
                'adzuna':        count_src(france_jobs, 'adzuna'),
                'jooble':        count_src(france_jobs, 'jooble'),
                'indeed':        count_src(france_jobs, 'indeed'),
                'jobtome':       count_src(france_jobs, 'jobtome'),
            },
        },
        'aupair': {
            'total': len(aupair_jobs),
            'by_city': {
                'barcelona': count_city(aupair_jobs, 'barcelona'),
                'palma':     count_city(aupair_jobs, 'palma'),
                'madrid':    count_city(aupair_jobs, 'madrid'),
            },
            'by_source': {
                'adzuna_es': count_src(aupair_jobs, 'adzuna_es'),
                'jooble':    count_src(aupair_jobs, 'jooble'),
                'indeed':    count_src(aupair_jobs, 'indeed'),
                'infojobs':  count_src(aupair_jobs, 'infojobs'),
                'jobtome':   count_src(aupair_jobs, 'jobtome'),
            },
        },
    }

    # ── SAUVEGARDE ──
    print("\n💾 Sauvegarde des fichiers JSON...")
    save_json(DATA_DIR / 'offres.json', france_jobs)
    save_json(DATA_DIR / 'aupair.json', aupair_jobs)
    save_json(DATA_DIR / 'meta.json', meta)

    elapsed = round(time.time() - start, 1)
    print(f"\n⏱  Terminé en {elapsed}s")
    print(f"   🇫🇷 {len(france_jobs)} offres IDF  |  🇪🇸 {len(aupair_jobs)} offres Au Pair")

    # ── GIT PUSH ──
    if push and GITHUB_AUTO_PUSH:
        print("\n📤 Push GitHub...")
        git_push(f"data: mise à jour offres {ts}")

    print(f"\n{'='*55}\n")


if __name__ == '__main__':
    if '--test' in sys.argv:
        # Mode test : vérifie uniquement le filtre IDF
        print("Test du filtre IDF :")
        tests = [
            ("Paris (75)",          "75001", "FR",  True),
            ("Paris, TX",           "",      "",    False),
            ("Paris, Tennessee",    "",      "",    False),
            ("Paris, Ontario",      "",      "",    False),
            ("Île-de-France",       "",      "FR",  True),
            ("Neuilly-sur-Seine",   "",      "FR",  True),
            ("Versailles (78)",     "78000", "FR",  True),
            ("Saint-Denis (93)",    "93200", "FR",  True),
            ("Lyon",                "",      "FR",  False),
            ("Marseille",           "",      "FR",  False),
            ("Boulogne-Billancourt","92100", "FR",  True),
            ("London",              "",      "GB",  False),
            ("Barcelona",           "",      "ES",  False),
            ("Évry-Courcouronnes",  "91080", "FR",  True),
        ]
        ok = 0
        for loc, cp, country, expected in tests:
            result = is_idf(loc, cp, country)
            status = "[OK]  " if result == expected else "[FAIL]"
            if result == expected:
                ok += 1
            print(f"  {status} is_idf({loc!r}, cp={cp!r}, country={country!r}) -> {result} (expected: {expected})")
        print(f"\n{ok}/{len(tests)} tests passés")
    else:
        push = '--no-push' not in sys.argv
        run(push=push)
