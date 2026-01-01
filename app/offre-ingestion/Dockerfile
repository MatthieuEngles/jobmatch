FROM python:3.12.3-slim

WORKDIR /app

# Copier et installer le package jobmatch-shared
COPY shared /tmp/jobmatch-shared
RUN pip install --no-cache-dir "/tmp/jobmatch-shared[embeddings]"

# Copier et installer les dépendances Python
COPY app/offre-ingestion/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le code source
COPY app/offre-ingestion/src/ ./src/
COPY app/offre-ingestion/scripts/entrypoint.sh /entrypoint.sh

# Rendre le script exécutable
RUN chmod +x /entrypoint.sh

# Point d'entrée principal
ENTRYPOINT ["/entrypoint.sh"]
