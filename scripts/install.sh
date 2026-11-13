#!/bin/bash
# Assistant Core - One-Command Installer
set -e

echo "🤖 Installing Assistant Core..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker Desktop first."
    exit 1
fi

# Check Docker Compose
if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose."
    exit 1
fi

# Create data directories
mkdir -p ./data/chromadb ./data/tenants

# Pull Ollama
echo "📦 Pulling Ollama..."
docker pull ollama/ollama:latest

# Start Ollama
echo "🚀 Starting Ollama..."
docker run -d --name ollama \
    -p 11437:11437 \
    -v ollama_data:/root/.ollama \
    --restart unless-stopped \
    ollama/ollama:latest

# Wait for Ollama
sleep 5

# Pull model from env or default
MODEL=${OLLAMA_MODEL:-llama3.2:3b}
echo "🧠 Pulling model: $MODEL"
docker exec ollama ollama pull $MODEL

# Build Assistant Core
echo "🔨 Building Assistant Core..."
docker build -t assistant-core .

# Start Assistant Core
echo "🎯 Starting Assistant Core..."
docker run -d --name assistant-core \
    -p 8037:8037 \
    -v $(pwd)/data:/app/data \
    --link ollama:ollama \
    -e OLLAMA_HOST=http://ollama:11437 \
    -e OLLAMA_MODEL=llama3.2:3b \
    -e PERSONA_NAME=JARVIS \
    -e PERSONA_STYLE="professional, concise, proactive" \
    -e VOICE_ENABLED=true \
    -e AUTO_UPDATE=true \
    --restart unless-stopped \
    assistant-core:latest

echo "✅ Assistant Core installed!"
echo "🌐 Web UI: http://localhost:8037"
echo "📚 API Docs: http://localhost:8037/docs"
echo ""
echo "Model flexibility:"
echo "  Ollama: any model from ollama.com/library (llama3.2, mistral, codellama, phi3, etc.)"
echo "  Set OLLAMA_MODEL env var to change (default: llama3.2:3b)"
echo "  For vision: llava, for coding: codellama, for speed: phi3"
echo ""
echo "Other model sources (via compatible APIs):"
echo "  Hugging Face: any GGUF model via ollama pull hf.co/user/model"
echo "  NVIDIA: Nemotron, Nemotron-3-Ultra via build.nvidia.com"
echo "  Custom GGUF: ollama create -f Modelfile"
echo ""
echo "Configure connectors via environment variables:"
echo "  GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN"
echo "  GOOGLE_CALENDAR_CREDENTIALS"
echo "  NOTION_TOKEN"
echo "  OBSIDIAN_VAULT_PATH"
echo "  SLACK_BOT_TOKEN"
echo "  GITHUB_TOKEN"
echo "  CRM_API_KEY"
echo ""
echo "For billing, set:"
echo "  STRIPE_SECRET_KEY"
echo "  STRIPE_WEBHOOK_SECRET"
echo "  STRIPE_PRICE_STARTER, STRIPE_PRICE_PRO, STRIPE_PRICE_ENTERPRISE"