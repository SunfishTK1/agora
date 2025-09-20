#!/usr/bin/env python
"""
Test domain creation via POST request.
"""

import requests
import re

# Get the form page first to extract CSRF token
session = requests.Session()

# Get the create form page
form_response = session.get('http://127.0.0.1:8002/dashboard/domains/create/')
print(f"Form page status: {form_response.status_code}")

if form_response.status_code == 200:
    # Extract CSRF token
    csrf_pattern = r'name="csrfmiddlewaretoken" value="([^"]+)"'
    csrf_match = re.search(csrf_pattern, form_response.text)
    
    if csrf_match:
        csrf_token = csrf_match.group(1)
        print(f"CSRF token found: {csrf_token[:20]}...")
        
        # Test domain data
        domain_data = {
            'csrfmiddlewaretoken': csrf_token,
            'name': 'Test Domain',
            'base_url': 'https://example.com/',
            'protocol': 'https',
            'max_depth': 2,
            'max_pages': 50,
            'scrape_frequency_hours': 24,
            'status': 'active',
            'advanced_config': '{}',
        }
        
        # Submit the form
        create_response = session.post(
            'http://127.0.0.1:8002/dashboard/domains/create/',
            data=domain_data,
            headers={
                'Referer': 'http://127.0.0.1:8002/dashboard/domains/create/'
            }
        )
        
        print(f"Create response status: {create_response.status_code}")
        print(f"Response URL: {create_response.url}")
        
        if create_response.status_code == 200:
            print("✅ Domain creation form works!")
        else:
            print(f"❌ Error: {create_response.status_code}")
            print(create_response.text[:500])
    else:
        print("❌ CSRF token not found in form")
        print(form_response.text[:500])
else:
    print(f"❌ Failed to load form page: {form_response.status_code}")
