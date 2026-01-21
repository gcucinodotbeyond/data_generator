import http.server
import socketserver
import webbrowser
import os
import sys

# Set port, default to 8000
PORT = 8000

# Change to the project root directory (parent of tools/)
# This ensures that 'data/...' paths are accessible from the root
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
os.chdir(project_root)

Handler = http.server.SimpleHTTPRequestHandler

try:
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}/visualizer.html"
        print(f"Serving at {url}")
        print(f"Project Root: {project_root}")
        print("Press Ctrl+C to stop.")
        
        # Open browser
        webbrowser.open(url)
        
        httpd.serve_forever()
except OSError as e:
    print(f"Error starting server on port {PORT}: {e}")
    print("Try a different port or check if it's already in use.")
except KeyboardInterrupt:
    print("\nServer stopped.")
