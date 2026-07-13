"""Backend/frontend process management for AnnoABSA CLI."""

import os
import sys
import subprocess
import threading
import time
import socket
import signal
import atexit
import re

from cli.config import ABSAAnnotatorConfig

# Global variable to track backend process
backend_process = None
shutdown_flag = threading.Event()


def cleanup_backend():
    """Clean up backend process on exit."""
    global backend_process
    if backend_process and backend_process.poll() is None:
        print("\n🧹 Cleaning up backend process...")
        backend_process.terminate()
        try:
            backend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            backend_process.kill()


def signal_handler(signum, frame):
    """Handle interrupt signals."""
    print("\n🛑 Received interrupt signal. Shutting down...")
    shutdown_flag.set()
    cleanup_backend()


# Register cleanup functions
atexit.register(cleanup_backend)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def is_port_in_use(host: str, port: int) -> bool:
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def update_vite_port_config(port: int, host: str):
    """Update vite.config.js with the specified port and host."""
    vite_config_path = "vite.config.js"
    if not os.path.exists(vite_config_path):
        return

    # Read current config
    with open(vite_config_path, 'r') as f:
        content = f.read()

    # Replace the server configuration
    pattern = r'server:\s*\{[^}]*\}'
    replacement = f'''server: {{
    port: {port},
    host: '{host}',
    open: true
  }}'''

    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)
        with open(vite_config_path, 'w') as f:
            f.write(content)


def start_backend(port: int = 8000, host: str = "localhost", data_path: str = None, config: ABSAAnnotatorConfig = None):
    """Start the FastAPI backend server."""
    global backend_process
    try:
        # Check if port is already in use
        if is_port_in_use(host, port):
            print(f"⚠️  Port {port} is already in use on {host}")
            print(
                f"💡 Backend might already be running on http://{host}:{port}")
            return

        print(f"🚀 Starting backend server on {host}:{port}...")
        if data_path:
            os.environ['ABSA_DATA_PATH'] = data_path
        if config:
            # Save config to temporary file for backend to read
            os.makedirs("temp", exist_ok=True)
            config_file = os.path.join("temp", "temp_absa_config.json")
            config.save_config(config_file)
            os.environ['ABSA_CONFIG_PATH'] = config_file

        backend_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn",
            "main:app", "--reload", f"--port={port}", f"--host={host}"
        ])

        # Wait for process to finish or shutdown signal
        while backend_process.poll() is None and not shutdown_flag.is_set():
            time.sleep(0.1)

        if shutdown_flag.is_set():
            cleanup_backend()

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start backend server: {e}")
        if not shutdown_flag.is_set():
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Backend server stopped by user")
        cleanup_backend()


def start_frontend(port: int = 3000, host: str = "localhost", backend_host: str = "localhost", backend_port: int = 8000):
    """Start the React frontend development server."""
    frontend_path = os.path.join(os.getcwd(), "frontend")
    if not os.path.exists(frontend_path):
        print("❌ Frontend directory not found! Make sure you're in the project root.")
        return False

    try:
        print(f"🌐 Starting frontend development server on {host}:{port}...")
        os.chdir(frontend_path)

        # Set environment variables for Vite
        env = os.environ.copy()
        env["VITE_BACKEND_URL"] = f"http://{backend_host}:{backend_port}"

        # Update vite.config.js to use the specified port
        update_vite_port_config(port, host)

        subprocess.run(["npm", "run", "dev"], check=True, env=env)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start frontend server: {e}")
        return False
    except KeyboardInterrupt:
        print("\n🛑 Frontend server stopped by user")
        return True
    except FileNotFoundError:
        print("❌ npm not found! Please install Node.js and npm.")
        return False


def start_full_app(backend_port: int = 8000, backend_host: str = "localhost", frontend_port: int = 3000, frontend_host: str = "localhost", data_path: str = None, config: ABSAAnnotatorConfig = None):
    """Start both backend and frontend servers."""
    print("🚀 Starting AnnoABSA...")
    print("=" * 50)

    # Start backend in a separate thread
    backend_thread = threading.Thread(target=start_backend, args=(
        backend_port, backend_host, data_path, config))
    backend_thread.daemon = False  # Don't make it daemon so we can properly clean up
    backend_thread.start()

    # Wait a moment for backend to start
    print("⏳ Waiting for backend to initialize...")
    time.sleep(3)

    # Start frontend (this will block until stopped)
    try:
        start_frontend(frontend_port, frontend_host,
                       backend_host, backend_port)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down AnnoABSA...")
        shutdown_flag.set()
        cleanup_backend()
        # Wait for backend thread to finish
        if backend_thread.is_alive():
            backend_thread.join(timeout=5)

    # Check if shutdown was triggered
    if shutdown_flag.is_set():
        sys.exit(0)
