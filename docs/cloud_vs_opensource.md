# Cloud Services vs Alternatives Open Source

Guide des équivalents open source pour le développement local et les environnements on-premise.

Couvre : **GCP**, **AWS**, **Azure** et **Scaleway**.

## Tableau récapitulatif

| Service GCP | Alternative Open Source | Même API ? | Docker Image | Notes |
|-------------|------------------------|------------|--------------|-------|
| **Cloud Storage (GCS)** | MinIO | ✅ S3-compatible | `minio/minio` | GCS supporte aussi l'API S3 |
| **BigQuery** | bigquery-emulator | ✅ Oui | `ghcr.io/goccy/bigquery-emulator` | Beta, mais très utilisable |
| **Pub/Sub** | Emulateur officiel | ✅ Oui | `gcr.io/google.com/cloudsdktool/google-cloud-cli:emulators` | Fourni par Google |
| **Firestore** | Emulateur officiel | ✅ Oui | `gcr.io/google.com/cloudsdktool/google-cloud-cli:emulators` | Fourni par Google |
| **Datastore** | Emulateur officiel | ✅ Oui | `gcr.io/google.com/cloudsdktool/google-cloud-cli:emulators` | Fourni par Google |
| **Bigtable** | Emulateur officiel | ✅ Oui | `gcr.io/google.com/cloudsdktool/google-cloud-cli:emulators` | Fourni par Google |
| **Spanner** | Emulateur officiel | ✅ Oui | `gcr.io/cloud-spanner-emulator/emulator` | Fourni par Google |
| **Cloud SQL (PostgreSQL)** | PostgreSQL | ✅ Oui | `postgres:15` | Natif |
| **Cloud SQL (MySQL)** | MySQL/MariaDB | ✅ Oui | `mysql:8` / `mariadb:11` | Natif |
| **Memorystore (Redis)** | Redis | ✅ Oui | `redis:7` | Natif |
| **Cloud Tasks** | Emulateur officiel | ✅ Oui | - | Ou utiliser Celery |
| **Cloud Functions** | OpenFaaS / Knative | ❌ Non | `openfaas/gateway` | API différente |
| **Cloud Run** | Knative | ⚠️ Partiel | - | Concept similaire |
| **Vertex AI** | Ollama / LocalAI | ❌ Non | `ollama/ollama` | Pour LLMs locaux |
| **Secret Manager** | Vault (HashiCorp) | ❌ Non | `hashicorp/vault` | Ou variables d'env en local |
| **Cloud Logging** | Loki (Grafana) | ❌ Non | `grafana/loki` | Avec Promtail |
| **Cloud Monitoring** | Prometheus + Grafana | ❌ Non | `prom/prometheus` | Standard industrie |
| **Artifact Registry** | Harbor / Nexus | ❌ Non | `goharbor/harbor` | Registry Docker |
| **Cloud CDN** | Varnish / Nginx | ❌ Non | `varnish:stable` | Cache HTTP |
| **Load Balancer** | Nginx / Traefik / HAProxy | ❌ Non | `traefik:v3` | Reverse proxy |
| **Cloud DNS** | CoreDNS / PowerDNS | ❌ Non | `coredns/coredns` | DNS local |
| **Cloud Scheduler** | Ofelia / Cron | ❌ Non | `mcuadros/ofelia` | Cron pour Docker |
| **Workflows** | Temporal / Airflow | ❌ Non | `temporalio/auto-setup` | Orchestration |

---

## Détails par service

### Cloud Storage → MinIO

```yaml
# docker-compose.yml
services:
  minio:
    image: minio/minio
    ports:
      - "9000:9000"   # API S3
      - "9001:9001"   # Console web
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
```

```python
# Code Python compatible GCS et MinIO
import boto3

# Local (MinIO)
s3 = boto3.client('s3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id='minioadmin',
    aws_secret_access_key='minioadmin'
)

# Prod (GCS en mode S3)
s3 = boto3.client('s3',
    endpoint_url='https://storage.googleapis.com',
    # Credentials via Workload Identity
)

# Même code pour les deux
s3.upload_file('file.txt', 'my-bucket', 'file.txt')
```

**Liens:**
- [MinIO GitHub](https://github.com/minio/minio)
- [MinIO Python SDK](https://min.io/docs/minio/linux/developers/python/minio-py.html)

---

### BigQuery → bigquery-emulator

```yaml
services:
  bigquery:
    image: ghcr.io/goccy/bigquery-emulator:latest
    ports:
      - "9050:9050"
    command:
      - "--project=my-project"
      - "--dataset=silver"
      - "--dataset=gold"
```

```python
from google.cloud import bigquery

# Local
client = bigquery.Client(
    project="my-project",
    client_options={"api_endpoint": "http://localhost:9050"}
)

# Prod (GCP)
client = bigquery.Client(project="my-project")

# Même code pour les deux
query = "SELECT * FROM `my-project.gold.offers` LIMIT 10"
results = client.query(query)
```

**Limites:**
- Pas 100% des fonctions SQL (mais les courantes OK)
- Pas d'IAM
- Stockage SQLite (rapide mais limité)

**Liens:**
- [bigquery-emulator GitHub](https://github.com/goccy/bigquery-emulator)

---

### Pub/Sub → Emulateur officiel

```yaml
services:
  pubsub:
    image: gcr.io/google.com/cloudsdktool/google-cloud-cli:emulators
    command: gcloud beta emulators pubsub start --host-port=0.0.0.0:8085
    ports:
      - "8085:8085"
```

```python
import os
from google.cloud import pubsub_v1

# Configurer l'émulateur
os.environ["PUBSUB_EMULATOR_HOST"] = "localhost:8085"

# Même code qu'en prod
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path("my-project", "my-topic")
publisher.publish(topic_path, b"Hello World")
```

**Liens:**
- [Pub/Sub Emulator Doc](https://cloud.google.com/pubsub/docs/emulator)

---

### Firestore → Emulateur officiel

```yaml
services:
  firestore:
    image: gcr.io/google.com/cloudsdktool/google-cloud-cli:emulators
    command: gcloud emulators firestore start --host-port=0.0.0.0:8080
    ports:
      - "8080:8080"
```

```python
import os
from google.cloud import firestore

# Configurer l'émulateur
os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"

# Même code qu'en prod
db = firestore.Client(project="my-project")
doc_ref = db.collection("users").document("user1")
doc_ref.set({"name": "John", "age": 30})
```

**Liens:**
- [Firestore Emulator Doc](https://firebase.google.com/docs/emulator-suite/connect_firestore)

---

### Cloud Spanner → Emulateur officiel

```yaml
services:
  spanner:
    image: gcr.io/cloud-spanner-emulator/emulator
    ports:
      - "9010:9010"  # gRPC
      - "9020:9020"  # REST
```

```python
import os
from google.cloud import spanner

os.environ["SPANNER_EMULATOR_HOST"] = "localhost:9010"

client = spanner.Client(project="my-project")
instance = client.instance("my-instance")
database = instance.database("my-database")
```

**Liens:**
- [Spanner Emulator Doc](https://cloud.google.com/spanner/docs/emulator)

---

### Secret Manager → Variables d'environnement (local) / Vault (avancé)

**Option simple (recommandée pour dev):**
```python
import os

def get_secret(name: str) -> str:
    env_mode = os.getenv("ENV_MODE", "local")

    if env_mode == "local":
        # Lire depuis .env
        return os.getenv(name)
    else:
        # Lire depuis Secret Manager
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        # ...
```

**Option Vault (pour clusters):**
```yaml
services:
  vault:
    image: hashicorp/vault:1.15
    ports:
      - "8200:8200"
    environment:
      VAULT_DEV_ROOT_TOKEN_ID: root
    cap_add:
      - IPC_LOCK
```

**Liens:**
- [HashiCorp Vault](https://www.vaultproject.io/)

---

### Vertex AI / AI Platform → Ollama / LocalAI

```yaml
services:
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
```

```python
import requests

# Local (Ollama)
response = requests.post(
    "http://localhost:11434/api/generate",
    json={"model": "llama2", "prompt": "Hello"}
)

# Note: API différente de Vertex AI
# Utiliser une abstraction comme LangChain pour unifier
```

**Liens:**
- [Ollama](https://ollama.ai/)
- [LocalAI](https://localai.io/)

---

### Cloud Logging → Loki

```yaml
services:
  loki:
    image: grafana/loki:2.9.0
    ports:
      - "3100:3100"
    command: -config.file=/etc/loki/local-config.yaml

  promtail:
    image: grafana/promtail:2.9.0
    volumes:
      - /var/log:/var/log
      - ./promtail-config.yml:/etc/promtail/config.yml
    command: -config.file=/etc/promtail/config.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
```

**Liens:**
- [Grafana Loki](https://grafana.com/oss/loki/)

---

### Cloud Monitoring → Prometheus + Grafana

```yaml
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

**Liens:**
- [Prometheus](https://prometheus.io/)
- [Grafana](https://grafana.com/)

---

## Stack locale complète pour JobMatch

```yaml
# docker-compose.local.yml
version: "3.8"

services:
  # === Storage ===
  minio:
    image: minio/minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data

  # === BigQuery ===
  bigquery:
    image: ghcr.io/goccy/bigquery-emulator:latest
    ports:
      - "9050:9050"
    command:
      - "--project=job-match-v0"
      - "--dataset=silver"
      - "--dataset=gold"

  # === Database ===
  db:
    image: postgres:15
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: jobmatch
      POSTGRES_PASSWORD: localpassword
      POSTGRES_DB: jobmatch
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # === Cache ===
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # === Observability (optionnel) ===
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    profiles: ["monitoring"]

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    profiles: ["monitoring"]

volumes:
  minio_data:
  postgres_data:
```

---

## Pattern d'abstraction recommandé

```python
# app/shared/storage.py
import os
from abc import ABC, abstractmethod

class StorageClient(ABC):
    @abstractmethod
    def upload(self, bucket: str, key: str, data: bytes): pass

    @abstractmethod
    def download(self, bucket: str, key: str) -> bytes: pass

class MinIOStorage(StorageClient):
    def __init__(self):
        import boto3
        self.client = boto3.client('s3',
            endpoint_url=os.getenv('MINIO_ENDPOINT', 'http://localhost:9000'),
            aws_access_key_id=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
            aws_secret_access_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin')
        )
    # ...

class GCSStorage(StorageClient):
    def __init__(self):
        from google.cloud import storage
        self.client = storage.Client()
    # ...

def get_storage() -> StorageClient:
    env = os.getenv("ENV_MODE", "local")
    if env == "local":
        return MinIOStorage()
    return GCSStorage()
```

---

# AWS Services vs Alternatives Open Source

## Tableau récapitulatif AWS

| Service AWS | Alternative Open Source | Même API ? | Docker Image | Notes |
|-------------|------------------------|------------|--------------|-------|
| **S3** | MinIO | ✅ Oui | `minio/minio` | 100% compatible S3 |
| **DynamoDB** | DynamoDB Local | ✅ Oui | `amazon/dynamodb-local` | Émulateur officiel AWS |
| **SQS** | ElasticMQ | ✅ Oui | `softwaremill/elasticmq` | Compatible SQS |
| **SNS** | LocalStack | ✅ Oui | `localstack/localstack` | Multi-services |
| **Lambda** | LocalStack / OpenFaaS | ⚠️ Partiel | `localstack/localstack` | LocalStack recommandé |
| **RDS (PostgreSQL)** | PostgreSQL | ✅ Oui | `postgres:15` | Natif |
| **RDS (MySQL)** | MySQL/MariaDB | ✅ Oui | `mysql:8` | Natif |
| **ElastiCache (Redis)** | Redis | ✅ Oui | `redis:7` | Natif |
| **ElastiCache (Memcached)** | Memcached | ✅ Oui | `memcached:1.6` | Natif |
| **Kinesis** | LocalStack | ✅ Oui | `localstack/localstack` | Ou Kafka |
| **Athena** | Trino / Presto | ⚠️ Partiel | `trinodb/trino` | SQL compatible |
| **Redshift** | PostgreSQL + TimescaleDB | ⚠️ Partiel | `timescale/timescaledb` | Pas 100% compatible |
| **Secrets Manager** | Vault / LocalStack | ✅ (LocalStack) | `localstack/localstack` | |
| **Step Functions** | LocalStack / Temporal | ⚠️ Partiel | `localstack/localstack` | |
| **API Gateway** | Kong / Traefik | ❌ Non | `kong:3` | Concept similaire |
| **CloudWatch** | Prometheus + Grafana | ❌ Non | `prom/prometheus` | Standard industrie |
| **ECR** | Harbor / Registry | ❌ Non | `registry:2` | Docker Registry |
| **ECS/EKS** | Kubernetes (k3s/kind) | ❌ Non | `rancher/k3s` | Orchestration |
| **Cognito** | Keycloak | ❌ Non | `quay.io/keycloak/keycloak` | Auth/IAM |
| **SES** | MailHog / Mailpit | ❌ Non | `mailhog/mailhog` | Email testing |

---

## LocalStack - Émulateur AWS tout-en-un

LocalStack émule la majorité des services AWS avec une compatibilité API.

```yaml
# docker-compose.yml
services:
  localstack:
    image: localstack/localstack:latest
    ports:
      - "4566:4566"           # Gateway unifié
      - "4510-4559:4510-4559" # Services externes
    environment:
      - SERVICES=s3,sqs,sns,dynamodb,lambda,secretsmanager,kinesis
      - DEBUG=1
      - DOCKER_HOST=unix:///var/run/docker.sock
    volumes:
      - "${LOCALSTACK_VOLUME_DIR:-./volume}:/var/lib/localstack"
      - "/var/run/docker.sock:/var/run/docker.sock"
```

```python
import boto3

# Configuration pour LocalStack
def get_aws_client(service: str):
    env = os.getenv("ENV_MODE", "local")

    if env == "local":
        return boto3.client(
            service,
            endpoint_url='http://localhost:4566',
            aws_access_key_id='test',
            aws_secret_access_key='test',
            region_name='us-east-1'
        )
    else:
        # Prod AWS
        return boto3.client(service)

# Exemple S3
s3 = get_aws_client('s3')
s3.create_bucket(Bucket='my-bucket')
s3.upload_file('file.txt', 'my-bucket', 'file.txt')

# Exemple DynamoDB
dynamodb = get_aws_client('dynamodb')
dynamodb.create_table(
    TableName='users',
    KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
    AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
    BillingMode='PAY_PER_REQUEST'
)

# Exemple SQS
sqs = get_aws_client('sqs')
queue = sqs.create_queue(QueueName='my-queue')
sqs.send_message(QueueUrl=queue['QueueUrl'], MessageBody='Hello')
```

**Liens:**
- [LocalStack GitHub](https://github.com/localstack/localstack)
- [LocalStack Documentation](https://docs.localstack.cloud/)

---

## DynamoDB Local (officiel AWS)

```yaml
services:
  dynamodb:
    image: amazon/dynamodb-local
    ports:
      - "8000:8000"
    command: "-jar DynamoDBLocal.jar -sharedDb -dbPath /data"
    volumes:
      - dynamodb_data:/data
```

```python
import boto3

dynamodb = boto3.resource('dynamodb',
    endpoint_url='http://localhost:8000',
    region_name='us-east-1',
    aws_access_key_id='fake',
    aws_secret_access_key='fake'
)

table = dynamodb.create_table(
    TableName='users',
    KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
    AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
    BillingMode='PAY_PER_REQUEST'
)
```

**Liens:**
- [DynamoDB Local Doc](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html)

---

## ElasticMQ (compatible SQS)

```yaml
services:
  elasticmq:
    image: softwaremill/elasticmq-native
    ports:
      - "9324:9324"   # SQS API
      - "9325:9325"   # UI
```

```python
import boto3

sqs = boto3.client('sqs',
    endpoint_url='http://localhost:9324',
    region_name='us-east-1',
    aws_access_key_id='x',
    aws_secret_access_key='x'
)

# Même API que SQS
queue = sqs.create_queue(QueueName='my-queue')
sqs.send_message(QueueUrl=queue['QueueUrl'], MessageBody='test')
```

**Liens:**
- [ElasticMQ GitHub](https://github.com/softwaremill/elasticmq)

---

# Azure Services vs Alternatives Open Source

## Tableau récapitulatif Azure

| Service Azure | Alternative Open Source | Même API ? | Docker Image | Notes |
|---------------|------------------------|------------|--------------|-------|
| **Blob Storage** | Azurite | ✅ Oui | `mcr.microsoft.com/azure-storage/azurite` | Émulateur officiel |
| **Table Storage** | Azurite | ✅ Oui | `mcr.microsoft.com/azure-storage/azurite` | Émulateur officiel |
| **Queue Storage** | Azurite | ✅ Oui | `mcr.microsoft.com/azure-storage/azurite` | Émulateur officiel |
| **Cosmos DB** | Cosmos DB Emulator | ✅ Oui | `mcr.microsoft.com/cosmosdb/linux/azure-cosmos-emulator` | Émulateur officiel |
| **SQL Database** | SQL Server / PostgreSQL | ✅ Oui | `mcr.microsoft.com/mssql/server` | Natif |
| **Service Bus** | RabbitMQ + Plugin | ⚠️ Partiel | `rabbitmq:3-management` | Pas 100% compatible |
| **Event Hubs** | Kafka | ⚠️ Partiel | `confluentinc/cp-kafka` | Protocol compatible |
| **Functions** | Azure Functions Core Tools | ✅ Oui | - | CLI local |
| **Key Vault** | Vault (HashiCorp) | ❌ Non | `hashicorp/vault` | |
| **Redis Cache** | Redis | ✅ Oui | `redis:7` | Natif |
| **Container Registry** | Harbor / Registry | ❌ Non | `registry:2` | |
| **Application Insights** | Jaeger / Zipkin | ❌ Non | `jaegertracing/all-in-one` | Tracing |
| **Logic Apps** | n8n / Temporal | ❌ Non | `n8nio/n8n` | Workflow |
| **API Management** | Kong / Traefik | ❌ Non | `kong:3` | |
| **Active Directory** | Keycloak | ❌ Non | `quay.io/keycloak/keycloak` | IAM |

---

## Azurite - Émulateur Azure Storage officiel

```yaml
services:
  azurite:
    image: mcr.microsoft.com/azure-storage/azurite
    ports:
      - "10000:10000"  # Blob
      - "10001:10001"  # Queue
      - "10002:10002"  # Table
    volumes:
      - azurite_data:/data
    command: "azurite --blobHost 0.0.0.0 --queueHost 0.0.0.0 --tableHost 0.0.0.0"
```

```python
from azure.storage.blob import BlobServiceClient

# Local (Azurite) - Use well-known emulator credentials
# See: https://docs.microsoft.com/en-us/azure/storage/common/storage-use-azurite#well-known-storage-account-and-key
connection_string = (
    "DefaultEndpointsProtocol=http;"
    "AccountName=devstoreaccount1;"
    "AccountKey=<AZURITE_WELL_KNOWN_KEY>;"  # Use key from docs link above
    "BlobEndpoint=http://localhost:10000/devstoreaccount1;"
)

# Prod (Azure)
# connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

client = BlobServiceClient.from_connection_string(connection_string)

# Même code
container = client.get_container_client("my-container")
container.create_container()
blob = container.get_blob_client("my-file.txt")
blob.upload_blob(b"Hello World")
```

**Liens:**
- [Azurite GitHub](https://github.com/Azure/Azurite)
- [Azurite Documentation](https://docs.microsoft.com/en-us/azure/storage/common/storage-use-azurite)

---

## Cosmos DB Emulator

```yaml
services:
  cosmosdb:
    image: mcr.microsoft.com/cosmosdb/linux/azure-cosmos-emulator
    ports:
      - "8081:8081"   # HTTPS endpoint
      - "10251-10254:10251-10254"
    environment:
      - AZURE_COSMOS_EMULATOR_PARTITION_COUNT=10
      - AZURE_COSMOS_EMULATOR_ENABLE_DATA_PERSISTENCE=true
    volumes:
      - cosmos_data:/tmp/cosmos/appdata
```

```python
from azure.cosmos import CosmosClient

# Local (Emulator) - Use well-known emulator credentials
# See: https://docs.microsoft.com/en-us/azure/cosmos-db/emulator#authenticate-requests
endpoint = "https://localhost:8081"
key = "<COSMOS_EMULATOR_WELL_KNOWN_KEY>"  # Use key from docs link above

# Prod
# endpoint = os.getenv("COSMOS_ENDPOINT")
# key = os.getenv("COSMOS_KEY")

client = CosmosClient(endpoint, key)
database = client.create_database_if_not_exists("mydb")
container = database.create_container_if_not_exists("mycontainer", partition_key="/id")
```

**Liens:**
- [Cosmos DB Emulator Doc](https://docs.microsoft.com/en-us/azure/cosmos-db/linux-emulator)

---

## Azure Functions Local

```bash
# Installation
npm install -g azure-functions-core-tools@4

# Créer un projet
func init MyFunctionApp --python
cd MyFunctionApp
func new --name HttpTrigger --template "HTTP trigger"

# Lancer localement
func start
```

**Liens:**
- [Azure Functions Core Tools](https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local)

---

# Scaleway Services vs Alternatives Open Source

## Tableau récapitulatif Scaleway

| Service Scaleway | Alternative Open Source | Même API ? | Docker Image | Notes |
|------------------|------------------------|------------|--------------|-------|
| **Object Storage** | MinIO | ✅ S3-compatible | `minio/minio` | Scaleway utilise API S3 |
| **Managed Database (PostgreSQL)** | PostgreSQL | ✅ Oui | `postgres:15` | Natif |
| **Managed Database (MySQL)** | MySQL/MariaDB | ✅ Oui | `mysql:8` | Natif |
| **Managed Database (Redis)** | Redis | ✅ Oui | `redis:7` | Natif |
| **Serverless Functions** | OpenFaaS / Knative | ❌ Non | `openfaas/gateway` | |
| **Serverless Containers** | Docker / Podman | ❌ Non | - | Concept similaire |
| **Messaging (NATS)** | NATS | ✅ Oui | `nats:latest` | Scaleway utilise NATS |
| **Messaging (SQS)** | ElasticMQ | ✅ S3-compatible | `softwaremill/elasticmq` | API SQS |
| **Container Registry** | Harbor / Registry | ❌ Non | `registry:2` | |
| **Kubernetes (Kapsule)** | k3s / kind / minikube | ❌ Non | `rancher/k3s` | |
| **Transactional Email** | MailHog / Mailpit | ❌ Non | `mailhog/mailhog` | |
| **Secret Manager** | Vault | ❌ Non | `hashicorp/vault` | |
| **Cockpit (Observability)** | Prometheus + Grafana | ❌ Non | `prom/prometheus` | |

---

## Object Storage Scaleway → MinIO

Scaleway Object Storage est compatible S3, donc MinIO fonctionne parfaitement.

```yaml
services:
  minio:
    image: minio/minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"
```

```python
import boto3

def get_s3_client():
    env = os.getenv("ENV_MODE", "local")

    if env == "local":
        return boto3.client('s3',
            endpoint_url='http://localhost:9000',
            aws_access_key_id='minioadmin',
            aws_secret_access_key='minioadmin'
        )
    else:
        # Scaleway Object Storage
        return boto3.client('s3',
            endpoint_url='https://s3.fr-par.scw.cloud',
            aws_access_key_id=os.getenv('SCW_ACCESS_KEY'),
            aws_secret_access_key=os.getenv('SCW_SECRET_KEY'),
            region_name='fr-par'
        )

s3 = get_s3_client()
s3.upload_file('file.txt', 'my-bucket', 'file.txt')
```

---

## NATS Messaging (utilisé par Scaleway)

```yaml
services:
  nats:
    image: nats:latest
    ports:
      - "4222:4222"   # Client
      - "8222:8222"   # Monitoring
    command: "--jetstream"
```

```python
import asyncio
import nats

async def main():
    # Local ou Scaleway - même API
    nc = await nats.connect("nats://localhost:4222")

    # Publish
    await nc.publish("my-subject", b"Hello NATS")

    # Subscribe
    sub = await nc.subscribe("my-subject")
    async for msg in sub.messages:
        print(f"Received: {msg.data.decode()}")

asyncio.run(main())
```

**Liens:**
- [NATS Documentation](https://docs.nats.io/)

---

# Tableau comparatif multi-cloud

| Catégorie | GCP | AWS | Azure | Scaleway | Open Source |
|-----------|-----|-----|-------|----------|-------------|
| **Object Storage** | Cloud Storage | S3 | Blob Storage | Object Storage | MinIO |
| **NoSQL Document** | Firestore | DynamoDB | Cosmos DB | - | MongoDB |
| **NoSQL Key-Value** | Memorystore | ElastiCache | Redis Cache | Managed Redis | Redis |
| **Message Queue** | Pub/Sub | SQS/SNS | Service Bus | SQS/NATS | RabbitMQ/NATS |
| **Serverless** | Cloud Functions | Lambda | Functions | Functions | OpenFaaS |
| **Data Warehouse** | BigQuery | Redshift/Athena | Synapse | - | Trino/ClickHouse |
| **Secret Manager** | Secret Manager | Secrets Manager | Key Vault | Secret Manager | Vault |
| **Container Registry** | Artifact Registry | ECR | ACR | Registry | Harbor |
| **Kubernetes** | GKE | EKS | AKS | Kapsule | k3s/kind |
| **IAM/Auth** | Cloud IAM | IAM/Cognito | AD/B2C | IAM | Keycloak |
| **Monitoring** | Cloud Monitoring | CloudWatch | App Insights | Cockpit | Prometheus |
| **Logging** | Cloud Logging | CloudWatch Logs | Log Analytics | Cockpit | Loki |

---

# Stack locale universelle

Cette stack fonctionne pour développer localement, quel que soit le cloud cible.

```yaml
# docker-compose.local.yml
version: "3.8"

services:
  # === Storage (S3-compatible) ===
  minio:
    image: minio/minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data

  # === Database SQL ===
  postgres:
    image: postgres:15
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: localpassword
      POSTGRES_DB: app
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # === Database NoSQL ===
  mongodb:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

  # === Cache ===
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # === Message Queue ===
  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"   # AMQP
      - "15672:15672" # Management UI
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest

  # === Email Testing ===
  mailhog:
    image: mailhog/mailhog
    ports:
      - "1025:1025"  # SMTP
      - "8025:8025"  # Web UI

  # === Auth/IAM ===
  keycloak:
    image: quay.io/keycloak/keycloak:latest
    ports:
      - "8080:8080"
    environment:
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: admin
    command: start-dev
    profiles: ["auth"]

  # === Monitoring ===
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    profiles: ["monitoring"]

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    profiles: ["monitoring"]

volumes:
  minio_data:
  postgres_data:
  mongo_data:
```

---

## Références

- [GCP Emulators Documentation](https://cloud.google.com/sdk/gcloud/reference/beta/emulators)
- [LocalStack Documentation](https://docs.localstack.cloud/)
- [Azurite Documentation](https://docs.microsoft.com/en-us/azure/storage/common/storage-use-azurite)
- [MinIO Documentation](https://min.io/docs/minio/linux/index.html)
- [bigquery-emulator GitHub](https://github.com/goccy/bigquery-emulator)
- [CNCF Landscape](https://landscape.cncf.io/) - Vue d'ensemble des outils cloud-native
