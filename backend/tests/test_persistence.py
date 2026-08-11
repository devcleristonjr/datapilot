import pandas as pd

import main


def test_dataset_persistence_roundtrip(tmp_path, monkeypatch):
    db_path = tmp_path / "datapilot_test.db"
    monkeypatch.setattr(main, "DATABASE_PATH", str(db_path))
    main.DATASETS_DB.clear()
    main.ensure_storage_db()

    dataset_id = "dataset-123"
    df = pd.DataFrame({"nome": ["Ana", "Ana", "Bruno"], "valor": [10, 10, 30]})
    main.DATASETS_DB[dataset_id] = {"filename": "teste.csv", "df": df, "cleaned_df": None}

    main.save_dataset(dataset_id)
    main.DATASETS_DB.clear()

    loaded = main.load_datasets_from_storage()

    assert dataset_id in loaded
    assert loaded[dataset_id]["filename"] == "teste.csv"
    assert loaded[dataset_id]["df"].equals(df)
