from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


def test_upload_accepts_valid_csv(tmp_path):
    file_path = tmp_path / "sample.csv"
    file_path.write_text("nome,idade\nAna,30\nBruno,25\n", encoding="utf-8")

    with file_path.open("rb") as f:
        response = client.post(
            "/api/upload",
            files={"file": (file_path.name, f, "text/csv")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert "dataset_id" in payload
    assert payload["rows_count"] == 2


def test_upload_rejects_invalid_format(tmp_path):
    file_path = tmp_path / "sample.txt"
    file_path.write_text("texto simples", encoding="utf-8")

    with file_path.open("rb") as f:
        response = client.post(
            "/api/upload",
            files={"file": (file_path.name, f, "text/plain")},
        )

    assert response.status_code == 400
    assert "Formato não suportado" in response.json()["detail"]
