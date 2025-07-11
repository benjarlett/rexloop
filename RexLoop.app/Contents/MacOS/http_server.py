import http.server
import socketserver
import os
import sys

PORT = 3000 # Frontend port

# Determine the base directory for static files
# In a PyInstaller bundle, sys._MEIPASS is the path to the temporary folder
# where PyInstaller extracts all bundled files.
if getattr(sys, 'frozen', False):
    # Running in a PyInstaller bundle
    STATIC_FILES_DIR = os.path.join(sys._MEIPASS, 'frontend_dist')
else:
    # Running as a script (for testing)
    STATIC_FILES_DIR = os.path.join(os.path.dirname(__file__), 'frontend_dist')

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_FILES_DIR, **kwargs)

print(f"Serving frontend from: {STATIC_FILES_DIR} on port {PORT}")

with socketserver.TCPServer(('', PORT), Handler) as httpd:
    print(f"HTTP server started on port {PORT}")
    httpd.serve_forever()
