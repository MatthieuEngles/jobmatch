# Terraform Apply - JobMatch Production

**Date**: 2025-01-05
**Project**: job-match-v0
**Region**: europe-west1

## Resume

| Action | Nombre |
|--------|--------|
| A creer | 5 |
| A modifier | 2 |
| A detruire | 4 |

## Ressources creees

### VM Compute
- `google_compute_instance.main` - VM jobmatch-vm (e2-medium, europe-west1-b)
  - IP statique: **35.189.200.57**
  - Disque: 50GB pd-balanced
  - Image: ubuntu-2204-lts

### Network
- `google_compute_address.static` - IP statique (35.189.200.57)
- `google_compute_subnetwork.main` - Subnet europe-west1

### Storage (recrees - changement de region)
- `google_storage_bucket.bronze` - jobmatch-bronze-job-match-v0
- `google_storage_bucket.backups` - jobmatch-backups-job-match-v0

## Ressources modifiees

### BigQuery Datasets
- `google_bigquery_dataset.silver` - delete_contents_on_destroy = true
- `google_bigquery_dataset.gold` - delete_contents_on_destroy = true

## Ressources detruites (anciennes - europe-west9)

- `google_compute_subnetwork.main` (europe-west9)
- `google_compute_address.static` (34.155.66.221)
- `google_storage_bucket.bronze` (europe-west9)
- `google_storage_bucket.backups` (europe-west9)

## Outputs

```
VM Instance:
  Name:        jobmatch-vm
  External IP: 35.189.200.57
  Zone:        europe-west1-b

SSH Command:
  gcloud compute ssh jobmatch-vm --zone=europe-west1-b --project=job-match-v0

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

## Service Accounts

| Service Account | Email |
|-----------------|-------|
| VM | jobmatch-vm-sa@job-match-v0.iam.gserviceaccount.com |
| Deploy (GitHub Actions) | deploy-sa@job-match-v0.iam.gserviceaccount.com |
| Terraform | terraform-sa@job-match-v0.iam.gserviceaccount.com |

## Secrets GCP (a configurer)

```bash
# 1. Mot de passe PostgreSQL
echo -n "MotDePasseSecurise123!" | gcloud secrets versions add postgres-password --data-file=-

# 2. Django Secret Key
python3 -c "import secrets; print(secrets.token_urlsafe(50))" | gcloud secrets versions add django-secret-key --data-file=-

# 3. BigQuery Gold SA Key
gcloud secrets versions add bigquery-gold-sa-key --data-file=/chemin/vers/bigquery-gold-key.json
```

## Prochaines etapes

1. Ajouter les secrets dans GCP Secret Manager (voir ci-dessus)
2. Configurer les GitHub Variables:
   - `GCP_PROJECT_ID` = `job-match-v0`
   - `GCP_WORKLOAD_IDENTITY_PROVIDER` = `projects/323309663680/locations/global/workloadIdentityPools/github-pool/providers/github-provider`
   - `GCP_DEPLOY_SERVICE_ACCOUNT` = `deploy-sa@job-match-v0.iam.gserviceaccount.com`
   - `VM_NAME` = `jobmatch-vm`
3. Creer l'environnement GitHub `production`
4. Push sur main pour declencher le deploiement

## Acces a la VM

```bash
# SSH
gcloud compute ssh jobmatch-vm --zone=europe-west1-b --project=job-match-v0

# Application (apres deploiement)
http://35.189.200.57
```
