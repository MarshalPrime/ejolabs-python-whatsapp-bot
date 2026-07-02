import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.services.kabisa_ingestion import collect_kabisa_documents
from app.services.qdrant_service import upsert_documents


def main():
    app = create_app()
    with app.app_context():
        documents = collect_kabisa_documents()
        count = upsert_documents(documents)
        print(f"Ingested {count} Kabisa documents into Qdrant.")


if __name__ == "__main__":
    main()
