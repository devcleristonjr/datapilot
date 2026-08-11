from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


def test_history_lists_uploaded_datasets():
    main.DATASETS_DB.clear()
    main.ensure_storage_db()
    main.DATASETS_DB["dataset-history-test"] = {
        "filename": "historico.csv",
        "df": __import__("pandas").DataFrame({"nome": ["Ana"]}),
        "cleaned_df": None,
    }
    main.save_dataset("dataset-history-test")

    response = client.get("/api/datasets")

    assert response.status_code == 200
    payload = response.json()
    assert "datasets" in payload
    assert any(item["dataset_id"] == "dataset-history-test" for item in payload["datasets"])
