import json
import pathlib
import subprocess
import sys
import tempfile
import time

import requests

BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent
VENV_PY = BACKEND_DIR / ".venv312" / "Scripts" / "python.exe"


def main():
    proc = subprocess.Popen(
        [str(VENV_PY), "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8001"],
        cwd=str(BACKEND_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        for _ in range(60):
            try:
                health = requests.get("http://127.0.0.1:8001/health", timeout=1)
                if health.ok:
                    break
            except requests.RequestException:
                time.sleep(0.2)
        else:
            raise RuntimeError("Backend não respondeu ao healthcheck.")

        csv_path = pathlib.Path(tempfile.gettempdir()) / "datapilot_test_upload.csv"
        csv_path.write_text("nome,idade\nAna,30\nBruno,25\n", encoding="utf-8")

        with csv_path.open("rb") as f:
            upload = requests.post(
                "http://127.0.0.1:8001/api/upload",
                files={"file": (csv_path.name, f, "text/csv")},
                timeout=20,
            )

        print("HEALTH", health.status_code, health.json())
        print("UPLOAD", upload.status_code, upload.json())

        payload = upload.json()
        dataset_id = payload["dataset_id"]

        profile = requests.get(f"http://127.0.0.1:8001/api/profile/{dataset_id}", timeout=10)
        preview = requests.get(f"http://127.0.0.1:8001/api/dataset/{dataset_id}/preview", timeout=10)

        print("PROFILE", profile.status_code, profile.json())
        print("PREVIEW", preview.status_code, preview.json())
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
