#!/bin/bash
set -e
echo ""
echo "╔══════════════════════════════════════╗"
echo "║   Rhadix v131  —  start              ║"
echo "║   Frontend : http://localhost:5174   ║"
echo "║   Backend  : http://localhost:8010   ║"
echo "╚══════════════════════════════════════╝"
echo ""
docker compose -p rhadix-v131 up --build -d
echo ""
echo "✓ Rhadix v131 draait. Open http://localhost:5174"
echo "  Logs bekijken: docker compose -p rhadix-v131 logs -f"
echo "  Stoppen:       docker compose -p rhadix-v131 down"
