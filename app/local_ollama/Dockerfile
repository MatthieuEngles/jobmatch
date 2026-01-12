# Local Ollama server with ministral models
FROM ollama/ollama:latest

# Copy the entrypoint script
COPY app/local_ollama/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Download models during build
# Start Ollama temporarily to pull models
RUN ollama serve & \
    sleep 5 && \
    ollama pull mistral:latest && \
    ollama pull mistral:7b && \
    pkill ollama

# Expose the Ollama API port
EXPOSE 11434

# Use custom entrypoint to start Ollama server
ENTRYPOINT ["/entrypoint.sh"]
