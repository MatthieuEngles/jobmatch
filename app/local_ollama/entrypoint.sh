#!/bin/bash

echo "Starting Ollama server..."
echo "Available models:"
ollama list

# Start Ollama server (foreground)
exec ollama serve
