"""Server entry point."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from smart_home_project.common.protocol import Protocol
from smart_home_project.server.smart_home_server import SmartHomeServer
from smart_home_project.server.server_settings import ServerSettings


def configure_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the smart-home TCP server")
    parser.add_argument("--host", default=None, help="Host/IP to bind")
    parser.add_argument("--port", default=None, type=int, help="TCP port")
    parser.add_argument("--settings", default=None, help="Path to server_settings.json")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    settings_path = Path(args.settings) if args.settings else base_dir / "server_settings.json"
    settings = ServerSettings.load(settings_path)
    configure_logging(settings.resolve(base_dir, settings.log_file))
    server = SmartHomeServer(args.host, args.port, settings_path)
    try:
        server.start()
    except KeyboardInterrupt:
        logging.getLogger("smart_home.server").info("Stopping server")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
