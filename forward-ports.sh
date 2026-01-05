#!/usr/bin/env bash

# VSCode Port Forwarding Script for JobMatch Services
# This script forwards all service ports so you can access them in your local browser

echo "🚀 Setting up port forwarding for JobMatch services..."
echo ""

# Load environment variables if .env exists
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Define ports with defaults from docker-compose.yml
GUI_PORT=${GUI_PORT:-8085}
CV_INGESTION_PORT=${CV_INGESTION_PORT:-8081}
AI_ASSISTANT_PORT=${AI_ASSISTANT_PORT:-8084}
OFFRE_INGESTION_PORT=${OFFRE_INGESTION_PORT:-8082}
MATCHING_PORT=${MATCHING_PORT:-8086}
DB_PORT=${DB_PORT:-5433}
REDIS_PORT=${REDIS_PORT:-6379}

echo "📋 Ports to forward:"
echo "-------------------"
echo "  Port $GUI_PORT - GUI (Main Application)"
echo "  Port $CV_INGESTION_PORT - CV Ingestion API"
echo "  Port $AI_ASSISTANT_PORT - AI Assistant API"
echo "  Port $OFFRE_INGESTION_PORT - Offre Ingestion API"
echo "  Port $MATCHING_PORT - Matching API"
echo "  Port $DB_PORT - PostgreSQL Database"
echo "  Port $REDIS_PORT - Redis Cache"
echo ""

# Check if running in VSCode terminal
if [ -z "$VSCODE_IPC_HOOK_CLI" ]; then
    echo "⚠️  Warning: Not running in VSCode terminal"
    echo "   This script works best when run from VSCode's integrated terminal"
    echo ""
fi

echo "📍 To forward ports in VSCode:"
echo "----------------------------"
echo "1. Open the 'Ports' panel (View → Ports)"
echo "2. Click 'Forward a Port' button"
echo "3. Add these ports one by one:"
echo ""
echo "   $GUI_PORT - GUI (Main Application)"
echo "   $CV_INGESTION_PORT - CV Ingestion API"
echo "   $AI_ASSISTANT_PORT - AI Assistant API"
echo "   $OFFRE_INGESTION_PORT - Offre Ingestion API"
echo "   $MATCHING_PORT - Matching API"
echo "   $DB_PORT - PostgreSQL Database"
echo "   $REDIS_PORT - Redis Cache"
echo ""
echo "4. Access your services at:"
echo "   GUI:              http://localhost:$GUI_PORT"
echo "   CV Ingestion:     http://localhost:$CV_INGESTION_PORT"
echo "   AI Assistant:     http://localhost:$AI_ASSISTANT_PORT"
echo "   Offre Ingestion:  http://localhost:$OFFRE_INGESTION_PORT"
echo "   Matching:         http://localhost:$MATCHING_PORT"
echo "   PostgreSQL:       localhost:$DB_PORT"
echo "   Redis:            localhost:$REDIS_PORT"
echo ""
echo "💡 Pro tip: VSCode automatically detects running Docker containers"
echo "   and prompts to forward ports in the bottom-right corner!"
echo ""
