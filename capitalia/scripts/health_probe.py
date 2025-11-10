from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request

from capitalia.config import Config


def main() -> None:
    host = os.environ.get("HEALTH_HOST", "127.0.0.1")
    timeout = float(os.environ.get("HEALTH_TIMEOUT", "2"))
    port_spec = os.environ.get("PORT_POOL") or os.environ.get("PORT", "8000-8100")
    candidates = [port for port in Config._parse_port_candidates(port_spec) if port != 0]

    for port in candidates:
        url = f"http://{host}:{port}/health"
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                if 200 <= resp.getcode() < 400:
                    return
        except urllib.error.URLError:
            continue
        except Exception:
            continue

    raise SystemExit("no healthy instance found in pool")


if __name__ == "__main__":
    main()
