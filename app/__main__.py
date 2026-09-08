"""Run the application with uvicorn using the configured host and port.

Usage: ``python -m app``. Binds to ``127.0.0.1`` by default. When
``TLS_CERTFILE``/``TLS_KEYFILE`` are set (see ``deploy/macos/certs.sh``), the
server speaks HTTPS so microphone/clipboard APIs work on the LAN.
"""

from __future__ import annotations

import uvicorn

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    ssl_keyfile = settings.tls_keyfile or None
    ssl_certfile = settings.tls_certfile or None
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
        log_level="info",
    )


if __name__ == "__main__":
    main()
