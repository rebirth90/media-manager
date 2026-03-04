import os
import sys
import threading
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication

# Allow absolute imports from the src package
sys.path.insert(0, os.path.dirname(__file__))

from src.services.api_server import run_server
from src.core.app_controller import AppController

def main() -> None:
    load_dotenv()
    
    server_host: str = os.getenv("SERVER_HOST", "127.0.0.1")
    port_str: str = os.getenv("LOCAL_PORT", "9000")

    try:
        server_port: int = int(port_str)
    except ValueError:
        server_port = 9000

    server_thread = threading.Thread(
        target=run_server,
        args=(server_host, server_port),
        daemon=True
    )
    server_thread.start()

    from assets.style_dark import GLOBAL_STYLESHEET

    qt_app = QApplication(sys.argv)
    qt_app.setStyleSheet(GLOBAL_STYLESHEET)
    
    font = qt_app.font()
    font.setFamily("Segoe UI")
    qt_app.setFont(font)

    # Pass control of the application lifecycle to the AppController
    app_controller = AppController()
    app_controller.run()
    
    sys.exit(qt_app.exec())

if __name__ == "__main__":
    main()
