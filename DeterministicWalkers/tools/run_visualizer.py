import subprocess
import webbrowser
import os
import sys
import time

# Set port
PORT = 8000

# Change to the project root directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
os.chdir(project_root)

# Check if visualizer_server.py exists
server_script = os.path.join("tools", "visualizer_server.py")
if not os.path.exists(server_script):
    print(f"Error: Server script not found at {server_script}")
    sys.exit(1)

url = f"http://localhost:{PORT}"
print(f"Starting Visualizer Server at {url}")
print(f"Project Root: {project_root}")

try:
    # Use 'py' launcher if available, otherwise 'python'
    python_cmd = "py" if subprocess.run(["py", "--version"], capture_output=True).returncode == 0 else "python"
    
    # Start the server in the background
    # We use -m uvicorn tools.visualizer_server:app or just run the script
    process = subprocess.Popen([python_cmd, server_script])
    
    print("Waiting for server to start...")
    time.sleep(2) # Give it a moment to bind to the port
    
    # Open browser
    print(f"Opening browser at {url}")
    webbrowser.open(url)
    
    print("Press Ctrl+C to stop the server.")
    process.wait()

except KeyboardInterrupt:
    print("\nStopping server...")
    if 'process' in locals():
        process.terminate()
except Exception as e:
    print(f"Error: {e}")
