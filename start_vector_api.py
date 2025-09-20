#!/usr/bin/env python
"""
Startup script for the Vector Search API server.
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraping_platform.settings')
django.setup()

# Now import and run the FastAPI server
from vector_search_api import run_server

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Start Vector Search API server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8001, help='Port to bind to')
    
    args = parser.parse_args()
    
    print(f"Starting Vector Search API server on {args.host}:{args.port}")
    run_server(host=args.host, port=args.port)
