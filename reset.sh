#!/bin/bash
set -e
echo ""
echo "⚠  Rhadix v131 volledig herinstalleren"
echo "   Dit verwijdert de database en bouwt alles opnieuw."
echo ""
read -p "Weet je het zeker? (ja/nee): " confirm
if [ "$confirm" != "ja" ]; then
  echo "Geannuleerd."
  exit 0
fi
echo ""
echo "Stoppen en volumes verwijderen..."
docker compose -p rhadix-v131 down -v
echo "Opnieuw bouwen en starten..."
docker compose -p rhadix-v131 up --build -d
echo ""
echo "✓ Herinstallatie voltooid. Open http://localhost:5174"
