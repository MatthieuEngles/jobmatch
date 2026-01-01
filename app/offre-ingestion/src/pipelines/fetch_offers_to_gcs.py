"""
fetch_offers_to_gcs.py

Récupère les offres quotidiennes (API France Travail) et écrit un JSON unique dans un bucket GCS,
de façon atomique et idempotente.

Usage:
  python fetch_offers_to_gcs.py [YYYY-MM-DD]
  Sans argument, prend la veille (UTC).

Variables d'environnement requises:
- FT_CLIENT_ID
- FT_CLIENT_SECRET
- GCS_BUCKET  (nom du bucket)
Optionnelles:
- GCS_PREFIX (défaut: "france_travail/offers")
- FT_SCOPE, FT_OAUTH_URL, FT_API_URL_BASE, FT_ROMECODES_PATH
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from google.api_core.exceptions import PreconditionFailed
from google.cloud import storage


# ----------------------------
# Utilitaires .env (sans dépendance externe)
# ----------------------------
def load_dotenv(dotenv_path: Path) -> None:
    """
    Charge un .env simple (KEY=VALUE) dans os.environ si la variable n'existe pas déjà.
    """
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def require_env(name: str) -> str:
    """Récupère une variable d'env obligatoire, sinon exit(1)."""
    val = os.environ.get(name, "").strip()
    if not val:
        print(f"Erreur: variable d'environnement manquante: {name}")
        sys.exit(1)
    return val


def get_env(name: str, default: str) -> str:
    return os.environ.get(name, default).strip()


# ----------------------------
# Gestion de la date à requêter
# ----------------------------
def parse_target_date(argv: list[str]) -> date:
    """
    - Sans argument: prend la veille (UTC)
    - Avec argument: attend YYYY-MM-DD et prend ce jour-là
    """
    if len(argv) <= 1:
        return datetime.now(UTC).date() - timedelta(days=1)

    s = argv[1]
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        print("Erreur: argument date invalide. Format attendu: YYYY-MM-DD (ex: 2025-12-20)")
        sys.exit(1)


# ----------------------------
# Chargement config
# ----------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

# France Travail (obligatoires)
CLIENT_ID = require_env("FT_CLIENT_ID")
CLIENT_SECRET = require_env("FT_CLIENT_SECRET")

# GCS (obligatoire)
GCP_PROJECT_ID = require_env("GCP_PROJECT_ID")
GCS_BUCKET = require_env("GCS_BUCKET")
GCS_PREFIX = get_env("GCS_PREFIX", "france_travail/offers").strip("/")

# Optionnelles (France Travail)
SCOPE = get_env("FT_SCOPE", "api_offresdemploiv2 o2dsoffre")
OAUTH_URL = get_env(
    "FT_OAUTH_URL",
    "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire",
)
API_URL_BASE = get_env(
    "FT_API_URL_BASE",
    "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search",
)

DEFAULT_ROMECODES_PATH = PROJECT_ROOT / "src" / "data_persist" / "rome_codes.txt"
ROMECODES_PATH = Path(get_env("FT_ROMECODES_PATH", str(DEFAULT_ROMECODES_PATH))).resolve()

# Sécurité token
TOKEN_SKEW_SECONDS = 60
_token_cache: dict[str, Any] = {"access_token": None, "expires_at": 0.0}


def _now_epoch() -> float:
    return time.time()


def get_token(force_refresh: bool = False) -> str:
    """
    Récupère un token valide (cache + refresh).
    """
    if (
        not force_refresh
        and _token_cache["access_token"]
        and _now_epoch() < (_token_cache["expires_at"] - TOKEN_SKEW_SECONDS)
    ):
        return _token_cache["access_token"]

    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": SCOPE,
    }

    r = requests.post(
        OAUTH_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=data,
        timeout=30,
    )
    r.raise_for_status()
    payload = r.json()

    access_token = payload["access_token"]
    expires_in = int(payload.get("expires_in", 0))

    _token_cache["access_token"] = access_token
    _token_cache["expires_at"] = _now_epoch() + expires_in

    return access_token


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {get_token()}", "Accept": "application/json"}


def load_rome_codes(path: Path) -> list[str]:
    if not path.exists():
        print(f"Erreur: fichier ROMECODES introuvable: {path}")
        sys.exit(1)

    codes: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        codes.append(line)

    if not codes:
        print(f"Erreur: aucun ROMECODE dans {path}")
        sys.exit(1)
    return codes


def extract_total_from_content_range(content_range: str | None) -> int | None:
    # Exemple: "offres 0-149/591250"
    if not content_range:
        return None
    m = re.search(r"/\s*(\d+)\s*$", content_range)
    return int(m.group(1)) if m else None


# ----------------------------
# HTTP helpers
# ----------------------------
def get_with_auto_refresh(session: requests.Session, url: str, params: dict, timeout: int = 30) -> requests.Response:
    """
    Fait un GET.
    Si 401 -> refresh token -> retente 1 fois.
    """
    session.headers.update(auth_headers())
    r = session.get(url, params=params, timeout=timeout)

    if r.status_code != 401:
        return r

    get_token(force_refresh=True)
    session.headers.update(auth_headers())
    return session.get(url, params=params, timeout=timeout)


# ----------------------------
# GCS helpers
# ----------------------------
def build_gcs_object_name(prefix: str, target_date_: date) -> str:
    """
    Structure recommandée pour faciliter lifecycle/partition:
    gs://bucket/<prefix>/ingestion_date=YYYY-MM-DD/offer_YYYY-MM-DD.json
    """
    d = target_date_.isoformat()
    return f"{prefix}/ingestion_date={d}/offer_{d}.json"


def upload_json_to_gcs_atomic(
    *,
    bucket_name: str,
    object_name: str,
    payload: dict[str, Any],
    content_type: str = "application/json; charset=utf-8",
    if_not_exists: bool = True,
) -> str:
    """
    Upload JSON vers GCS.

    Atomicité / idempotence:
    - if_not_exists=True => utilise la précondition if_generation_match=0 :
      l'upload échoue si l'objet existe déjà, empêchant d'écraser un fichier journalier.

    Retourne le gs:// URL.
    """

    client = storage.Client(project=GCP_PROJECT_ID)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    try:
        if if_not_exists:
            blob.upload_from_string(data, content_type=content_type, if_generation_match=0)
        else:
            blob.upload_from_string(data, content_type=content_type)
    except PreconditionFailed as err:
        # L'objet existe déjà (generation != 0)
        raise RuntimeError(
            f"Objet GCS déjà existant, upload refusé (idempotence): gs://{bucket_name}/{object_name}"
        ) from err

    return f"gs://{bucket_name}/{object_name}"


# ----------------------------
# Main
# ----------------------------
def main() -> int:
    debut = datetime.now(UTC)

    target_date = parse_target_date(sys.argv)
    min_dt = f"{target_date.isoformat()}T00:00:00Z"
    max_dt = f"{(target_date + timedelta(days=1)).isoformat()}T00:00:00Z"

    api_url = f"{API_URL_BASE}?minCreationDate={min_dt}&maxCreationDate={max_dt}"
    rome_codes = load_rome_codes(ROMECODES_PATH)

    gcs_object = build_gcs_object_name(GCS_PREFIX, target_date)

    print(f"ROMECODES: {len(rome_codes)} (depuis {ROMECODES_PATH})")
    print(f"Requête période: {min_dt} -> {max_dt}")
    print(f"URL: {api_url}")
    print(f"Destination GCS: gs://{GCS_BUCKET}/{gcs_object}")

    session = requests.Session()

    # Accumule toutes les offres en mémoire pour un unique write/upload à la fin.
    all_offers: list[dict[str, Any]] = []

    # Throttle: assurer au moins 0.11s entre deux requêtes API (début->début)
    MIN_API_INTERVAL = 0.11
    last_api_call_ts: float | None = None  # time.monotonic()

    for i, rome in enumerate(rome_codes, start=1):
        start = 0
        step = 150

        while True:
            range_str = f"{start}-{start + step - 1}"
            params = {"codeROME": rome, "range": range_str}

            try:
                # Assure l'intervalle minimum entre deux appels API (avant d'appeler l'API)
                now_ts = time.monotonic()
                if last_api_call_ts is not None:
                    elapsed = now_ts - last_api_call_ts
                    remaining = MIN_API_INTERVAL - elapsed
                    if remaining > 0:
                        time.sleep(remaining)

                r = get_with_auto_refresh(session, api_url, params=params, timeout=30)
                # Marque le début de CET appel API
                last_api_call_ts = time.monotonic()

                status = r.status_code
                total = extract_total_from_content_range(r.headers.get("Content-Range"))

                if status == 204:
                    print(f"{i}/{len(rome_codes)} {rome} range={range_str} -> 204 (0 offre)")
                    break

                if status in (200, 206):
                    payload = r.json() if r.content else {}
                    offers = payload.get("resultats") or []
                    offers_n = len(offers)

                    if offers:
                        all_offers.extend(offers)

                    print(
                        f"{i}/{len(rome_codes)} {rome} range={range_str} -> {status} ({offers_n} offres) total={total}"
                    )

                    if status == 206:
                        # Si on connaît le total, et que la prochaine page commencerait au-delà,
                        # inutile de refaire un appel (qui renverrait 0 offre / 204 ou équivalent).
                        if total is not None and (start + step) >= total:
                            break

                        start += step
                        continue

                    break

                # Tout autre status => stop pipeline
                body_snippet = (r.text or "")[:500]
                raise RuntimeError(
                    f"HTTP unexpected status={status} rome={rome} range={range_str} url={r.url} body={body_snippet!r}"
                )

            except RuntimeError:
                raise
            except Exception as e:
                raise RuntimeError(f"Failure rome={rome} range={range_str} url={api_url} params={params}") from e

    # Upload unique en fin de job (évite des milliers d'écritures)
    gcs_url = upload_json_to_gcs_atomic(
        bucket_name=GCS_BUCKET,
        object_name=gcs_object,
        payload={"resultats": all_offers},
        if_not_exists=True,
    )

    print(f"JSON uploadé: {gcs_url} (offres: {len(all_offers)})")
    fin = datetime.now(UTC)
    print(f"Durée totale du script: {(fin - debut).total_seconds():.2f} secondes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
