#!/usr/bin/env python
"""
Test recursive crawling capabilities of Agora crawler.
"""

import os
import sys
import django
import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraping_platform.settings')
django.setup()

from scraper.agora_crawler import get_agora_crawler_service

@csrf_exempt
def test_recursive_crawler(request):
    """Test recursive crawling capabilities."""

    if request.method == 'POST':
        start_url = request.POST.get('url', 'https://httpbin.org/')
        max_depth = int(request.POST.get('depth', '2'))
        max_pages = int(request.POST.get('pages', '10'))

        try:
            crawler = get_agora_crawler_service()
            result = crawler.crawl_recursive(
                start_url=start_url,
                max_depth=max_depth, 
                max_pages_per_level=max_pages
            )

            # Convert CrawlResult objects to dictionaries for JSON serialization
            serializable_result = {
                "crawl_results": [
                    {
                        "url": r.url,
                        "title": r.title,
                        "status": r.status,
                        "content": r.content[:500] + "..." if len(r.content) > 500 else r.content,  # Truncate long content
                        "full_content": r.content,  # Include full content
                        "content_length": len(r.content),
                        "children": r.children,
                        "robots_allowed": r.robots_allowed,
                        "crawl_delay": r.crawl_delay,
                        "processing_time": r.processing_time,
                        "status_code": r.status_code,
                        "error_message": r.error_message,
                        "depth": getattr(r, 'depth', 0)  # Add depth if available
                    } for r in result.get('crawl_results', [])
                ],
                "child_links": result.get('child_links', []),
                "total_pages": result.get('total_pages', 0),
                "successful_pages": result.get('successful_pages', 0),
                "failed_pages": result.get('failed_pages', 0),
                "robots_blocked_pages": result.get('robots_blocked_pages', 0),
                "processing_time": result.get('processing_time', 0),
                "start_url": result.get('start_url', start_url),
                "max_depth": result.get('max_depth', max_depth),
                "timestamp": result.get('timestamp', ''),
                "success": True
            }

            return HttpResponse(json.dumps(serializable_result), content_type='application/json')

        except Exception as e:
            error_data = {
                'error': str(e),
                'success': False
            }
            return HttpResponse(json.dumps(error_data), content_type='application/json')

    # GET request - show recursive crawling interface
    csrf_token = get_token(request)
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🔄 Agora Recursive Crawler - Full Content View</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 1000px; margin: 50px auto; padding: 20px; }}
            .container {{ background: #f5f5f5; padding: 20px; border-radius: 8px; }}
            .result {{ background: white; padding: 15px; margin: 20px 0; border-radius: 5px; max-height: 600px; overflow-y: auto; }}
            .success {{ background: #d4edda; border: 1px solid #c3e6cb; }}
            .error {{ background: #f8d7da; border: 1px solid #f5c6cb; }}
            .form-group {{ margin: 10px 0; }}
            .form-group label {{ display: inline-block; width: 120px; }}
            input[type="url"], input[type="number"] {{ padding: 8px; margin-right: 10px; }}
            input[type="url"] {{ width: 400px; }}
            input[type="number"] {{ width: 60px; }}
            button {{ padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; }}
            .crawl-tree {{ font-family: monospace; font-size: 12px; }}
            .depth-0 {{ color: #0066cc; font-weight: bold; }}
            .depth-1 {{ color: #0080ff; margin-left: 20px; }}
            .depth-2 {{ color: #4da6ff; margin-left: 40px; }}
            .depth-3 {{ color: #80c1ff; margin-left: 60px; }}
            .summary {{ background: #e7f3ff; padding: 10px; border-radius: 5px; margin-bottom: 15px; }}
            .content-preview {{ background: #f8f9fa; padding: 10px; margin: 5px 0; border-radius: 5px; border-left: 3px solid #007bff; }}
            .content-full {{ background: #ffffff; padding: 10px; margin: 5px 0; border-radius: 5px; border: 1px solid #ddd; max-height: 200px; overflow-y: auto; font-family: monospace; font-size: 12px; white-space: pre-wrap; }}
            .toggle-content {{ color: #007bff; cursor: pointer; text-decoration: underline; font-size: 12px; }}
            .page-result {{ margin-bottom: 20px; border: 1px solid #e9ecef; border-radius: 8px; padding: 15px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔄 Agora Recursive Crawler - Full Content View</h1>
            <p>Test the <strong>recursive crawling capabilities</strong> and view <strong>complete text content</strong> from all crawled pages!</p>

            <form id="crawlerForm" method="post">
                <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
                
                <div class="form-group">
                    <label>Start URL:</label>
                    <input type="url" name="url" id="urlInput" placeholder="Enter starting URL" 
                           value="https://httpbin.org/">
                </div>
                
                <div class="form-group">
                    <label>Max Depth:</label>
                    <input type="number" name="depth" id="depthInput" value="2" min="1" max="5">
                    <small>(How deep to crawl recursively)</small>
                </div>
                
                <div class="form-group">
                    <label>Pages/Level:</label>
                    <input type="number" name="pages" id="pagesInput" value="10" min="1" max="50">
                    <small>(Maximum pages per depth level)</small>
                </div>
                
                <button type="submit">🔄 Start Recursive Crawl</button>
            </form>

            <div id="result"></div>

            <div class="summary">
                <h3>🚀 Recursive Crawling Features:</h3>
                <ul>
                    <li><strong>🔄 Multi-Level Crawling:</strong> Crawls sub-paths recursively up to specified depth</li>
                    <li><strong>🎯 Sub-Path Filtering:</strong> Only follows links within the same domain and path hierarchy</li>
                    <li><strong>🤖 Robots.txt Compliance:</strong> Respects crawl delays at every level</li>
                    <li><strong>⚡ Performance Control:</strong> Configurable pages per level to control performance</li>
                    <li><strong>🛡️ Domain Boundaries:</strong> Automatically enforces domain restrictions</li>
                    <li><strong>📊 Rich Metadata:</strong> Tracks crawl depth, parent-child relationships</li>
                    <li><strong>📄 Full Content Display:</strong> View complete text content from all crawled pages</li>
                    <li><strong>🔍 Content Preview:</strong> Expandable content sections with character counts</li>
                </ul>
            </div>

            <div class="summary">
                <h3>🧪 Test URLs for Recursive Crawling:</h3>
                <ul>
                    <li><strong>https://httpbin.org/</strong> - API testing site (good for testing)</li>
                    <li><strong>https://example.com/</strong> - Simple site structure</li>
                    <li><strong>Your own domain</strong> - Test on your website</li>
                </ul>
            </div>
        </div>

        <script>
            document.getElementById('crawlerForm').onsubmit = function(e) {{
                e.preventDefault();
                const formData = new FormData(this);
                const resultDiv = document.getElementById('result');

                resultDiv.innerHTML = '<div class="result">⏳ Starting recursive crawl... Please wait</div>';

                fetch('', {{
                    method: 'POST',
                    body: formData
                }})
                .then(response => {{
                    if (!response.ok) {{
                        throw new Error('HTTP ' + response.status);
                    }}
                    return response.json();
                }})
                .then(data => {{
                    if (data.error) {{
                        resultDiv.innerHTML = `
                            <div class="result error">
                                <h3>❌ Crawl Failed</h3>
                                <p><strong>Error:</strong> ${{data.error}}</p>
                            </div>
                        `;
                        return;
                    }}

                    // Success - display comprehensive results
                    let html = `
                        <div class="result success">
                            <div class="summary">
                                <h3>✅ Recursive Crawl Complete!</h3>
                                <p><strong>Start URL:</strong> ${{data.start_url}}</p>
                                <p><strong>Total Pages:</strong> ${{data.total_pages}}</p>
                                <p><strong>Successful:</strong> ${{data.successful_pages}}</p>
                                <p><strong>Failed:</strong> ${{data.failed_pages}}</p>
                                <p><strong>Robots Blocked:</strong> ${{data.robots_blocked_pages}}</p>
                                <p><strong>Processing Time:</strong> ${{(data.processing_time || 0).toFixed(3)}}s</p>
                                <p><strong>Max Depth Used:</strong> ${{data.max_depth}}</p>
                            </div>
                            
                            <h4>🌳 Crawl Tree Structure:</h4>
                            <div class="crawl-tree">
                    `;

                    // Display crawl results with content
                    if (data.crawl_results && data.crawl_results.length > 0) {{
                        data.crawl_results.forEach((result, index) => {{
                            const depth = result.depth || 0;
                            const status_icon = result.status === 'success' ? '✅' : '❌';
                            const robots_icon = result.robots_allowed ? '🤖✅' : '🤖❌';
                            
                            html += `
                                <div class="page-result">
                                    <div class="depth-${{Math.min(depth, 3)}}">
                                        <strong>${{status_icon}} ${{robots_icon}} ${{result.url}}</strong>
                                        <small>(${{(result.processing_time || 0).toFixed(2)}}s, ${{(result.children && result.children.length) || 0}} children, ${{result.content_length || 0}} chars)</small>
                                    </div>
                                    
                                    ${{result.title ? `<div><strong>Title:</strong> ${{result.title}}</div>` : ''}}
                                    
                                    <div class="content-preview">
                                        <strong>Content Preview:</strong><br>
                                        ${{result.content || 'No content available'}}
                                        ${{result.content && result.content.length > 500 ? `
                                            <br><span class="toggle-content" onclick="toggleFullContent(${{index}})">🔽 Show Full Content (${{result.content_length}} characters)</span>
                                            <div id="full-content-${{index}}" class="content-full" style="display: none;">
                                                ${{result.full_content || result.content}}
                                            </div>
                                        ` : ''}}
                                    </div>
                                    
                                    ${{result.children && result.children.length > 0 ? `
                                        <div><strong>Child Links Found:</strong> ${{result.children.join(', ')}}</div>
                                    ` : ''}}
                                </div>
                            `;
                        }});
                    }} else {{
                        html += '<p>No detailed crawl results available</p>';
                    }}

                    html += `
                            </div>
                        </div>
                    `;

                    resultDiv.innerHTML = html;
                }})
                .catch(error => {{
                    resultDiv.innerHTML = `
                        <div class="result error">
                            <h3>❌ Request Failed</h3>
                            <p><strong>Error:</strong> ${{error.message}}</p>
                        </div>
                    `;
                }});
            }};
            
            // Function to toggle full content display
            function toggleFullContent(index) {{
                const fullContentDiv = document.getElementById(`full-content-${{index}}`);
                const toggle = event.target;
                
                if (fullContentDiv.style.display === 'none') {{
                    fullContentDiv.style.display = 'block';
                    toggle.innerHTML = `🔼 Hide Full Content`;
                }} else {{
                    fullContentDiv.style.display = 'none';
                    toggle.innerHTML = `🔽 Show Full Content`;
                }}
            }}
        </script>
    </body>
    </html>
    """

    return HttpResponse(html)

if __name__ == "__main__":
    print("🔄 Recursive Crawler Test Created!")
