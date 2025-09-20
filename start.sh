#!/bin/bash

echo "🚀 Starting Enterprise Scraping Platform..."

# Activate virtual environment
source .tkvenv/bin/activate

echo "✅ Virtual environment activated"

# Start Django server
echo "🌐 Starting Django server on http://127.0.0.1:8002"
python manage.py runserver 127.0.0.1:8002
