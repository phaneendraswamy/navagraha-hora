import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/seed_profile.py data/master_profile.json")
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    response = requests.post(f"{backend_url}/profile", json=payload, timeout=60)
    response.raise_for_status()
    print(response.json())


if __name__ == "__main__":
    main()
