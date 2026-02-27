import os
import sys
import threading
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication

from services.api_server import run_server
from ui.main_window import SecureServerWindow

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

    qt_app = QApplication(sys.argv)
    
    font = qt_app.font()
    font.setFamily("Segoe UI")
    qt_app.setFont(font)

    main_window = SecureServerWindow()
    main_window.show()
    
    sys.exit(qt_app.exec())

if __name__ == "__main__":
    main()
