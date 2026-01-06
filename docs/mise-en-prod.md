# Mise en Production - JobMatch

## Prérequis

- Accès au projet GCP `job-match-v0`
- Accès au repo GitHub `MatthieuEngles/jobmatch`
- Accès OVH pour le DNS (domaine `molp.fr`)

## Architecture de déploiement

```
Internet
    │
    ├── http://35.189.200.57 ──────┐
    │                              │
    └── https://jobmatch.molp.fr ──┼──► Caddy (port 80/443)
                                   │         │
                                   │         ▼
                                   │    localhost:8085 (GUI)
                                   │         │
                                   │    ┌────┴────────────────┐
                                   │    │  Docker Network     │
                                   │    ├─────────────────────┤
                                   │    │ gui:8085            │
                                   │    │ cv-ingestion:8081   │
                                   │    │ ai-assistant:8084   │
                                   │    │ matching:8086       │
                                   │    │ db:5432 (PostgreSQL)│
                                   │    │ redis:6379          │
                                   │    └─────────────────────┘
```

## Étapes de déploiement

### 1. Configurer le DNS (OVH)

Créer un enregistrement A chez OVH :
- **Type** : A
- **Sous-domaine** : jobmatch
- **Cible** : 35.189.200.57
- **TTL** : 3600

Vérifier la propagation (~5-30 min) :
```bash
dig jobmatch.molp.fr +short
# Doit retourner : 35.189.200.57
```

### 2. Merger sur main (déclenche le CD)

```bash
git checkout main
git merge dev
git push origin main
```

Le workflow GitHub Actions `deploy-prod.yml` se déclenche automatiquement et :
1. S'authentifie sur GCP via Workload Identity Federation
2. Se connecte à la VM via SSH
3. Pull le code depuis `main`
4. Récupère les secrets depuis GCP Secret Manager
5. Build et démarre les containers avec `docker-compose.prod.yml`

### 3. Configurer HTTPS sur la VM (après propagation DNS)

Se connecter à la VM :
```bash
gcloud compute ssh jobmatch-vm --zone=europe-west1-b --project=job-match-v0
```

Mettre à jour le Caddyfile :
```bash
sudo tee /etc/caddy/Caddyfile << 'EOF'
# JobMatch Caddyfile with HTTPS

jobmatch.molp.fr {
    reverse_proxy localhost:8085
    encode gzip

    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
    }
}

:80 {
    reverse_proxy localhost:8085
}
EOF

sudo systemctl reload caddy
sudo systemctl status caddy
```

Caddy obtiendra automatiquement un certificat Let's Encrypt.

### 4. Vérifier le déploiement

```bash
# Via IP (HTTP)
curl http://35.189.200.57/health/

# Via domaine (HTTPS) - après config DNS + Caddy
curl https://jobmatch.molp.fr/health/
```

## Secrets GCP

Les secrets sont stockés dans GCP Secret Manager (`job-match-v0`) :

| Secret | Description |
|--------|-------------|
| `postgres-password` | Mot de passe PostgreSQL |
| `django-secret-key` | Clé secrète Django |
| `bigquery-gold-sa-key` | Service Account JSON pour BigQuery (projet Mohamed) |

Le script `/opt/jobmatch/fetch-secrets.sh` sur la VM récupère ces secrets et génère le fichier `.env`.

## Variables GitHub

Configurées dans Settings > Variables > Actions :

| Variable | Valeur |
|----------|--------|
| `GCP_PROJECT_ID` | job-match-v0 |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | projects/.../providers/github |
| `GCP_DEPLOY_SERVICE_ACCOUNT` | deploy-sa@job-match-v0.iam.gserviceaccount.com |
| `VM_NAME` | jobmatch-vm |

## Commandes utiles sur la VM

```bash
# Se connecter
gcloud compute ssh jobmatch-vm --zone=europe-west1-b --project=job-match-v0

# Voir les logs
cd /opt/jobmatch
docker compose -f docker-compose.prod.yml logs -f

# Voir les logs d'un service spécifique
docker compose -f docker-compose.prod.yml logs -f gui

# Redémarrer les services
docker compose -f docker-compose.prod.yml restart

# Rebuild et redéployer
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml build --pull
docker compose -f docker-compose.prod.yml up -d

# Voir le status
docker compose -f docker-compose.prod.yml ps

# Exécuter les migrations Django
docker compose -f docker-compose.prod.yml exec gui python manage.py migrate

# Créer un superuser
docker compose -f docker-compose.prod.yml exec gui python manage.py createsuperuser
```

## Troubleshooting

### Le site n'est pas accessible

1. Vérifier que Caddy tourne :
   ```bash
   sudo systemctl status caddy
   sudo journalctl -u caddy -f
   ```

2. Vérifier que les containers tournent :
   ```bash
   docker compose -f docker-compose.prod.yml ps
   ```

3. Vérifier les logs GUI :
   ```bash
   docker compose -f docker-compose.prod.yml logs gui
   ```

### Erreur CSRF / 403 Forbidden

Vérifier que `CSRF_TRUSTED_ORIGINS` et `ALLOWED_HOSTS` sont bien configurés dans le `.env` :
```bash
cat /opt/jobmatch/.env | grep -E "(CSRF|ALLOWED)"
```

### Certificat SSL non obtenu

1. Vérifier que le DNS pointe bien vers l'IP :
   ```bash
   dig jobmatch.molp.fr +short
   ```

2. Vérifier les logs Caddy :
   ```bash
   sudo journalctl -u caddy -f
   ```

3. S'assurer que les ports 80 et 443 sont ouverts dans le firewall GCP.

### BigQuery / Matching ne fonctionne pas

Vérifier que le credential est bien monté :
```bash
docker compose -f docker-compose.prod.yml exec matching ls -la /app/credentials/
docker compose -f docker-compose.prod.yml exec matching cat /app/credentials/bigquery-gold-key.json | head -5
```

## Rollback

Pour revenir à une version précédente :

```bash
# Sur la VM
cd /opt/jobmatch
git fetch origin
git checkout <commit-sha>
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

## Monitoring

- **GitHub Actions** : https://github.com/MatthieuEngles/jobmatch/actions
- **GCP Console** : https://console.cloud.google.com/compute/instances?project=job-match-v0
- **Logs VM** : `sudo tail -f /var/log/startup-script.log`
