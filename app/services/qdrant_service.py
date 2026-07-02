import logging
import uuid

from flask import current_app

try:
    from qdrant_client import QdrantClient, models
except ImportError:  # pragma: no cover - exercised before dependencies are installed.
    QdrantClient = None
    models = None


def _client():
    if QdrantClient is None:
        logging.warning("qdrant-client is not installed")
        return None
    return QdrantClient(url=current_app.config["QDRANT_URL"])


def _ensure_collection(client, collection_name):
    try:
        client.get_collection(collection_name=collection_name)
    except Exception:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=client.get_fastembed_vector_params(),
        )


def upsert_documents(documents):
    """
    Store text documents in Qdrant using qdrant-client's local FastEmbed support.
    Each document must have: id, text, metadata.
    """
    if not documents:
        return 0

    client = _client()
    if client is None:
        return 0

    collection = current_app.config["QDRANT_COLLECTION"]
    _ensure_collection(client, collection)

    points = []
    vector_name = client.get_vector_field_name()
    for doc in documents:
        text = doc["text"]
        payload = {"document": text, **doc.get("metadata", {})}
        points.append(
            models.PointStruct(
                id=doc.get("id") or str(uuid.uuid4()),
                vector={
                    vector_name: models.Document(
                        text=text,
                        model=client.embedding_model_name,
                    )
                },
                payload=payload,
            )
        )

    client.upsert(
        collection_name=collection,
        points=points,
        wait=True,
    )
    return len(documents)


def search_knowledge(query, limit=5):
    client = _client()
    if client is None:
        return []

    try:
        response = client.query_points(
            collection_name=current_app.config["QDRANT_COLLECTION"],
            query=models.Document(text=query, model=client.embedding_model_name),
            using=client.get_vector_field_name(),
            limit=limit,
            with_payload=True,
        )
    except Exception as exc:
        logging.error("Qdrant search failed: %s", exc)
        return []

    normalized = []
    for result in response.points:
        payload = result.payload or {}
        normalized.append(
            {
                "text": payload.get("document", ""),
                "score": result.score,
                "metadata": payload,
            }
        )
    return normalized


def list_available_vehicles(limit=20):
    client = _client()
    if client is None:
        return []

    try:
        response = client.scroll(
            collection_name=current_app.config["QDRANT_COLLECTION"],
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="content_type",
                        match=models.MatchValue(value="vehicle"),
                    )
                ]
            ),
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
    except Exception as exc:
        logging.error("Qdrant vehicle listing failed: %s", exc)
        return []

    points, _ = response
    vehicles = []
    seen = set()
    for point in points:
        payload = point.payload or {}
        vehicle_id = payload.get("vehicle_id") or payload.get("source_url")
        if vehicle_id in seen:
            continue
        seen.add(vehicle_id)
        vehicles.append(
            {
                "text": payload.get("document", ""),
                "metadata": payload,
            }
        )
    return vehicles


def list_charging_stations(location=None, limit=12):
    client = _client()
    if client is None:
        return []

    try:
        response = client.scroll(
            collection_name=current_app.config["QDRANT_COLLECTION"],
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="content_type",
                        match=models.MatchValue(value="charger"),
                    ),
                    models.FieldCondition(
                        key="country",
                        match=models.MatchValue(value=current_app.config["KABISA_COUNTRY"].upper()),
                    ),
                ]
            ),
            limit=200,
            with_payload=True,
            with_vectors=False,
        )
    except Exception as exc:
        logging.error("Qdrant charger listing failed: %s", exc)
        return []

    points, _ = response
    chargers = []
    seen = set()
    for point in points:
        payload = point.payload or {}
        charger_id = payload.get("charger_id") or payload.get("kabisa_id") or payload.get("name")
        if charger_id in seen:
            continue
        seen.add(charger_id)
        if location and not _matches_charger_location(payload, location):
            continue
        chargers.append(
            {
                "text": payload.get("document", ""),
                "metadata": payload,
            }
        )
        if len(chargers) >= limit:
            break
    return chargers


def _matches_charger_location(payload, location):
    normalized = location.lower()
    searchable = " ".join(
        str(payload.get(key) or "")
        for key in ("name", "address", "document")
    ).lower()
    if normalized in searchable:
        return True

    if normalized == "kigali":
        latitude = payload.get("latitude")
        longitude = payload.get("longitude")
        return (
            isinstance(latitude, (int, float))
            and isinstance(longitude, (int, float))
            and -2.05 <= latitude <= -1.88
            and 30.0 <= longitude <= 30.18
        )
    return False


def collection_status():
    client = _client()
    if client is None:
        return {"reachable": False, "points_count": 0}

    try:
        info = client.get_collection(collection_name=current_app.config["QDRANT_COLLECTION"])
    except Exception as exc:
        logging.error("Qdrant collection status failed: %s", exc)
        return {"reachable": False, "points_count": 0}

    return {
        "reachable": True,
        "points_count": info.points_count or 0,
    }
