"""
Entry point for the Search-ADS server when running as a Tauri sidecar.

This script starts the FastAPI server and listens for shutdown commands from stdin.
"""

import argparse
import sys
import threading
import signal
import uvicorn
import logging
from pathlib import Path

class StreamToLogger(object):
    """
    Fake file-like stream object that redirects writes to a logger instance.
    """
    def __init__(self, logger, level):
       self.logger = logger
       self.level = level
       self.linebuf = ''

    def write(self, buf):
       for line in buf.rstrip().splitlines():
          self.logger.log(self.level, line.rstrip())

    def flush(self):
       pass

    def isatty(self):
       return False
       
    @property
    def encoding(self):
        return 'utf-8'

def setup_logging():
    """Setup logging to file in data directory."""
    try:
        log_dir = Path.home() / ".search-ads"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure root logger
        logging.basicConfig(
            filename=log_dir / "server.log",
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Redirect stdout/stderr to logging
        stdout_logger = logging.getLogger('STDOUT')
        sl = StreamToLogger(stdout_logger, logging.INFO)
        sys.stdout = sl
        
        stderr_logger = logging.getLogger('STDERR')
        sl_err = StreamToLogger(stderr_logger, logging.ERROR)
        sys.stderr = sl_err
        
        logging.info(f"Server starting. Home: {Path.home()}")
        logging.info(f"Data dir: {log_dir}")
        logging.info(f"Frozen: {getattr(sys, 'frozen', False)}")
        logging.info(f"Executable: {sys.executable}")
        
        # Fix SSL for frozen app
        import os
        if getattr(sys, 'frozen', False):
            # In PyInstaller, certifi cacert.pem is collected into certifi directory in sys._MEIPASS
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
            cert_path = os.path.join(base_path, 'certifi', 'cacert.pem')
            
            if os.path.exists(cert_path):
                os.environ['SSL_CERT_FILE'] = cert_path
                os.environ['REQUESTS_CA_BUNDLE'] = cert_path
                logging.info(f"Set SSL_CERT_FILE/REQUESTS_CA_BUNDLE to bundled cert: {cert_path}")
            else:
                logging.warning(f"Bundled certifi not found at {cert_path}. Checking generic location...")
                # Fallback to certifi.where() if it resolves meaningfully (unlikely in frozen but possible)
                import certifi
                if os.path.exists(certifi.where()):
                     os.environ['SSL_CERT_FILE'] = certifi.where()
                     os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
                     logging.info(f"Using default certifi location: {certifi.where()}")
                else:
                     logging.error("Could not find any CA bundle!")

        # Log API Keys presence
        from src.core.config import settings
        logging.info(f"Has OpenAI Key: {bool(settings.openai_api_key)}")
        logging.info(f"Has ADS Key: {bool(settings.ads_api_key)}")
        
        # Explicit check for .env file
        env_path = settings.data_dir / ".env"
        if env_path.exists():
            logging.info(f"Found .env file at {env_path}")
        else:
            logging.warning(f".env file NOT found at {env_path}")

        # Path Debugging
        logging.info(f"DB Path from settings: {settings.db_path}")
        logging.info(f"Chroma Path from settings: {settings.chroma_path}")
        
        # Verify visibility
        if settings.data_dir.exists():
            try:
                contents = list(settings.data_dir.iterdir())
                logging.info(f"Data dir contents: {[p.name for p in contents]}")
            except Exception as e:
                logging.error(f"Failed to list data dir: {e}")
            
    except Exception as e:
        # If logging setup fails, write to original stderr if possible
        sys.__stderr__.write(f"Failed to setup logging: {e}\n")


def stdin_listener(server: uvicorn.Server):
    """Listen for shutdown command from Tauri parent process."""
    try:
        for line in sys.stdin:
            cmd = line.strip().upper()
            if cmd == "SHUTDOWN":
                print("[Server] Received shutdown command", flush=True)
                server.should_exit = True
                break
    except Exception as e:
        print(f"[Server] stdin listener error: {e}", flush=True)


def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="Search-ADS Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=9527, help="Port to bind to")
    args = parser.parse_args()

    print(f"[Server] Starting Search-ADS server on {args.host}:{args.port}", flush=True)

    # Import the FastAPI app
    from src.web.main import app

    # Configure uvicorn
    config = uvicorn.Config(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
        access_log=True,
    )
    server = uvicorn.Server(config)

    # Start stdin listener thread for graceful shutdown
    stdin_thread = threading.Thread(target=stdin_listener, args=(server,), daemon=True)
    stdin_thread.start()

    # Handle SIGTERM for graceful shutdown
    def handle_sigterm(signum, frame):
        print("[Server] Received SIGTERM, shutting down...", flush=True)
        server.should_exit = True

    signal.signal(signal.SIGTERM, handle_sigterm)

    # Run the server
    try:
        server.run()
    except KeyboardInterrupt:
        print("[Server] Interrupted, shutting down...", flush=True)
    finally:
        print("[Server] Server stopped", flush=True)


if __name__ == "__main__":
    main()
