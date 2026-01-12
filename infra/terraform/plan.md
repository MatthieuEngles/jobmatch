# Terraform Plan - JobMatch Production

**Date**: 2025-01-05
**Project**: job-match-v0
**Region**: europe-west9

## Resume

| Action | Nombre |
|--------|--------|
| A creer | 14 |
| A modifier | 0 |
| A detruire et recreer | 2 |

## Ressources a creer (+)

### VM et Compute
- `google_compute_instance.main` - VM jobmatch-vm (e2-medium, europe-west9-a)
  - IP statique: 34.155.66.221
  - Disque: 50GB pd-balanced
  - Image: ubuntu-2204-lts

### APIs
- `google_project_service.apis["aiplatform.googleapis.com"]` - Vertex AI API
- `google_project_service.secretmanager` - Secret Manager API

### IAM
- `google_project_iam_member.vm_vertexai_user` - Role aiplatform.user pour la VM

### Secret Manager
- `google_secret_manager_secret.postgres_password`
- `google_secret_manager_secret.django_secret_key`
- `google_secret_manager_secret.bigquery_gold_sa_key`
- `google_secret_manager_secret_iam_member.vm_postgres_password`
- `google_secret_manager_secret_iam_member.vm_django_secret`
- `google_secret_manager_secret_iam_member.vm_bigquery_gold_sa_key`

### Storage IAM (re-creation due to state)
- `google_storage_bucket_iam_member.vm_bronze_admin`
- `google_storage_bucket_iam_member.vm_backups_admin`

## Ressources a detruire et recreer (-/+)

### BigQuery Datasets (changement de region: europe-west1 -> europe-west9)
- `google_bigquery_dataset.silver` - Dataset Silver
- `google_bigquery_dataset.gold` - Dataset Gold

**ATTENTION**: Les tables BigQuery seront perdues lors de la recreation des datasets!

## Outputs apres apply

```
VM Instance:
  Name:        jobmatch-vm
  External IP: 34.155.66.221
  Zone:        europe-west9-a

SSH Command:
  gcloud compute ssh jobmatch-vm --zone=europe-west9-a --project=job-match-v0

Storage:
  Bronze Bucket: jobmatch-bronze-job-match-v0
  Backups Bucket: jobmatch-backups-job-match-v0

BigQuery:
  Silver Dataset: jobmatch_silver
  Gold Dataset:   jobmatch_gold

GitHub Actions Variables (set in repo settings):
  GCP_PROJECT_ID:                  job-match-v0
  GCP_WORKLOAD_IDENTITY_PROVIDER:  projects/323309663680/locations/global/workloadIdentityPools/github-pool/providers/github-provider
  GCP_DEPLOY_SERVICE_ACCOUNT:      deploy-sa@job-match-v0.iam.gserviceaccount.com
  VM_NAME:                         jobmatch-vm
```

## Commande pour appliquer

```bash
cd infra/terraform
terraform apply
```

## Apres le apply

1. Ajouter les secrets dans GCP Secret Manager:
```bash
echo -n "MotDePasseSecurise123!" | gcloud secrets versions add postgres-password --data-file=-
python3 -c "import secrets; print(secrets.token_urlsafe(50))" | gcloud secrets versions add django-secret-key --data-file=-
gcloud secrets versions add bigquery-gold-sa-key --data-file=/chemin/vers/key.json
```

2. Configurer les GitHub Variables (voir outputs ci-dessus)

3. Push sur main pour declencher le deploiement
