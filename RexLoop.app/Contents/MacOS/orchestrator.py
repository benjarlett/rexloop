import subprocess
import os
import sys
import time
import logging
import socket
import atexit

# Configure logging
def setup_logging(log_dir):
    os.makedirs(log_dir, exist_ok=True)

    # Orchestrator log
    orchestrator_log_path = os.path.join(log_dir, 'orchestrator.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(orchestrator_log_path),
            logging.StreamHandler(sys.stdout) # Also log to console for direct debugging
        ]
    )
    logging.info(f"Orchestrator logs will be written to: {orchestrator_log_path}")

    # Backend log
    backend_log_path = os.path.join(log_dir, 'backend.log')
    backend_handler = logging.FileHandler(backend_log_path)
    backend_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    logging.getLogger('backend').addHandler(backend_handler)
    logging.getLogger('backend').setLevel(logging.INFO)
    logging.info(f"Backend logs will be written to: {backend_log_path}")

    # HTTP Server log
    http_server_log_path = os.path.join(log_dir, 'http_server.log')
    http_server_handler = logging.FileHandler(http_server_log_path)
    http_server_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    logging.getLogger('http_server').addHandler(http_server_handler)
    logging.getLogger('http_server').setLevel(logging.INFO)
    logging.info(f"HTTP Server logs will be written to: {http_server_log_path}")


def get_script_dir():
    # Determine the base directory for the script
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        return os.path.dirname(sys.executable)
    else:
        # Running as a script (for testing)
        return os.path.dirname(os.path.abspath(__file__))

def kill_process_on_port(port):
    logging.info(f"Checking for processes on port {port}...")
    try:
        # Use lsof to find PIDs listening on the port
        # -t: terse output (only PIDs)
        # -i :<port>: Internet files for the specified port
        command = ['lsof', '-t', '-i', f':{port}']
        pids = subprocess.check_output(command, text=True).strip().split('\n')
        pids = [p for p in pids if p] # Filter out empty strings

        if pids:
            logging.info(f"Found processes on port {port}: {', '.join(pids)}")
            for pid in pids:
                try:
                    logging.info(f"Killing process {pid} on port {port}...")
                    os.kill(int(pid), 9) # SIGKILL
                except ProcessLookupError:
                    logging.warning(f"Process {pid} not found, already terminated.")
                except Exception as e:
                    logging.error(f"Error killing process {pid}: {e}")
            time.sleep(1) # Give it a moment to release the port
            logging.info(f"Processes on port {port} terminated.")
        else:
            logging.info(f"No processes found on port {port}.")
    except subprocess.CalledProcessError:
        logging.info(f"No processes found on port {port} (lsof returned non-zero).")
    except FileNotFoundError:
        logging.error("lsof command not found. Cannot check for processes on port.")
    except Exception as e:
        logging.error(f"An unexpected error occurred during port check: {e}")

backend_process = None
http_server_process = None

def cleanup_processes():
    global backend_process, http_server_process
    logging.info("Shutting down RexLoop processes...")
    if backend_process and backend_process.poll() is None:
        logging.info(f"Terminating backend (PID: {backend_process.pid})...")
        backend_process.terminate()
        try:
            backend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logging.warning(f"Backend (PID: {backend_process.pid}) did not terminate gracefully, killing...")
            backend_process.kill()
    else:
        logging.info("Backend not running or already terminated.")

    if http_server_process and http_server_process.poll() is None:
        logging.info(f"Terminating HTTP server (PID: {http_server_process.pid})...")
        http_server_process.terminate()
        try:
            http_server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logging.warning(f"HTTP server (PID: {http_server_process.pid}) did not terminate gracefully, killing...")
            http_server_process.kill()
    else:
        logging.info("HTTP server not running or already terminated.")
    logging.info("RexLoop processes shut down.")

def main():
    global backend_process, http_server_process

    script_dir = get_script_dir()
    log_dir = os.path.join(script_dir, 'logs')
    setup_logging(log_dir)

    logging.info("Orchestrator started.")

    app_name = "RexLoop" # This should match APP_NAME in build_mac_app.sh
    backend_exec_path = os.path.join(script_dir, f'{app_name}-Backend')
    http_server_script_path = os.path.join(script_dir, 'http_server.py')
    frontend_port = 3000

    logging.info(f"Script directory: {script_dir}")
    logging.info(f"Backend executable path: {backend_exec_path}")
    logging.info(f"HTTP server script path: {http_server_script_path}")
    logging.info(f"Frontend port: {frontend_port}")

    # Register cleanup function to run on exit
    atexit.register(cleanup_processes)

    # Port cleanup
    kill_process_on_port(frontend_port)

    # Start backend
    logging.info("Starting RexLoop Backend...")
    try:
        backend_process = subprocess.Popen(
            [backend_exec_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1 # Line-buffered output
        )
        logging.info(f"Backend started with PID: {backend_process.pid}")
        # Start a thread to read backend output
        def read_backend_output():
            for line in backend_process.stdout:
                logging.getLogger('backend').info(line.strip())
            for line in backend_process.stderr:
                logging.getLogger('backend').error(line.strip())
        import threading
        threading.Thread(target=read_backend_output, daemon=True).start()

    except FileNotFoundError:
        logging.error(f"Backend executable not found at: {backend_exec_path}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error starting backend: {e}")
        sys.exit(1)

    # Start HTTP server for frontend
    logging.info("Starting HTTP Server for Frontend...")
    try:
        http_server_process = subprocess.Popen(
            [sys.executable, http_server_script_path], # Use sys.executable to ensure correct python interpreter
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1 # Line-buffered output
        )
        logging.info(f"HTTP Server started with PID: {http_server_process.pid}")
        # Start a thread to read http server output
        def read_http_server_output():
            for line in http_server_process.stdout:
                logging.getLogger('http_server').info(line.strip())
            for line in http_server_process.stderr:
                logging.getLogger('http_server').error(line.strip())
        import threading
        threading.Thread(target=read_http_server_output, daemon=True).start()

    except FileNotFoundError:
        logging.error(f"HTTP server script not found at: {http_server_script_path}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error starting HTTP server: {e}")
        sys.exit(1)

    # Give servers a moment to start
    time.sleep(2)

    # Open Frontend in browser
    frontend_url = f"http://localhost:{frontend_port}"
    logging.info(f"Opening Frontend in browser: {frontend_url}")
    try:
        subprocess.run(['open', frontend_url], check=True)
    except Exception as e:
        logging.error(f"Error opening browser: {e}")

    logging.info("RexLoop is running. Press Ctrl+C to stop.")
    # Keep the orchestrator running until processes terminate or script is interrupted
    try:
        while True:
            if backend_process.poll() is not None:
                logging.warning(f"Backend (PID: {backend_process.pid}) terminated unexpectedly with exit code {backend_process.returncode}.")
                break
            if http_server_process.poll() is not None:
                logging.warning(f"HTTP Server (PID: {http_server_process.pid}) terminated unexpectedly with exit code {http_server_process.returncode}.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Orchestrator interrupted by user.")
    except Exception as e:
        logging.error(f"An unexpected error occurred in orchestrator loop: {e}")
    finally:
        cleanup_processes() # Ensure cleanup on exit

if __name__ == "__main__":
    main()
