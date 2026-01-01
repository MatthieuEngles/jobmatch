#!/bin/bash
set -e  # Arrête le script si une commande échoue

# Router qui choisit quel script Python exécuter
case "$1" in
  fetch)
    echo "🚀 Exécution: Fetch offers to GCS..."
    python -u src/pipelines/fetch_offers_to_gcs.py "${@:2}"
    ;;
  silver)
    echo "🚀 Exécution: Transform to BigQuery Silver..."
    python -u src/pipelines/transform_offers_to_bigquery_silver.py "${@:2}"
    ;;
  gold)
    echo "🚀 Exécution: Transform to BigQuery Gold..."
    python -u src/pipelines/transform_offers_to_bigquery_gold.py "${@:2}"
    ;;
  *)
    echo "❌ Usage: $0 {fetch|silver|gold} [arguments optionnels]"
    exit 1
    ;;
esac
