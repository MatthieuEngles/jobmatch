import json
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# CONFIGURATION VIA VARIABLES D'ENVIRONNEMENT
# ============================================================

# URLs fixes
TOKEN_URL = os.getenv("TOKEN_URL")
API_URL = os.getenv("API_URL")

# Variables sensibles (doivent être définies dans l'environnement)
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
SCOPE = os.getenv("SCOPE")

# Paramètres fonctionnels
OUTPUT_FILE = os.getenv("OUTPUT_FILE")
RANGE = "0-149"

# ============================================================
# VÉRIFICATION DES VARIABLES D'ENVIRONNEMENT
# ============================================================

if not CLIENT_ID or not CLIENT_SECRET:
    print("Variables d'environnement manquantes :")
    print("- FRANCE_TRAVAIL_CLIENT_ID")
    print("- FRANCE_TRAVAIL_CLIENT_SECRET")
    sys.exit(1)

# ============================================================
# 1) OBTENTION DU TOKEN OAUTH2 (client_credentials)
# ============================================================

token_payload = {
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "scope": SCOPE,
}

token_headers = {"Content-Type": "application/x-www-form-urlencoded"}

token_response = requests.post(TOKEN_URL, data=token_payload, headers=token_headers, timeout=15)

if token_response.status_code != 200:
    print("Erreur lors de la récupération du token OAuth2")
    print(token_response.status_code, token_response.text)
    sys.exit(1)

access_token = token_response.json()["access_token"]

# ============================================================
# 2) APPEL DE L'API OFFRES D'EMPLOI
# ============================================================

api_headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

api_params = {"range": RANGE}

api_response = requests.get(API_URL, headers=api_headers, params=api_params, timeout=30)

# 200 = OK / 206 = Partial Content (pagination)
if api_response.status_code not in (200, 206):
    print("Erreur lors de l'appel à l'API Offres d'emploi")
    print(api_response.status_code, api_response.text)
    sys.exit(1)

# ============================================================
# 3) SAUVEGARDE DU JSON DANS data/requete.json
# ============================================================

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

data = api_response.json()

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Données France Travail enregistrées dans {OUTPUT_FILE}")
