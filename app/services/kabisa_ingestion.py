import uuid
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from flask import current_app


PAGE_PATHS = (
    "",
    "/shop",
    "/charge",
    "/maintenance",
    "/contact",
    "/financing",
    "/testdrive",
    "/FAQ",
)


def _stable_id(value):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, value))


def _clean_text(text):
    return " ".join(text.split())


def _page_documents():
    base_url = current_app.config["KABISA_SITE_BASE_URL"].rstrip("/")
    documents = []

    for path in PAGE_PATHS:
        url = urljoin(base_url + "/", path.lstrip("/"))
        response = requests.get(url, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        title = _clean_text(soup.title.get_text(" ")) if soup.title else url
        text = _clean_text(soup.get_text(" "))
        if not text:
            continue

        documents.append(
            {
                "id": _stable_id(url),
                "text": f"{title}\n{text}",
                "metadata": {
                    "source": "gokabisa_page",
                    "source_url": url,
                    "title": title,
                    "country": current_app.config["KABISA_COUNTRY"],
                    "content_type": "page",
                },
            }
        )
    return documents


def _vehicle_text(vehicle):
    fields = [
        f"{vehicle.get('year')} {vehicle.get('make')} {vehicle.get('model')}",
        f"Trim: {', '.join(vehicle.get('trim') or [])}",
        f"Category: {vehicle.get('category')}",
        f"Classification: {vehicle.get('classification')}",
        f"Range: {vehicle.get('range')} km",
        f"Battery capacity: {vehicle.get('batteryCapacity')} kWh",
        f"Price: {vehicle.get('price')} {vehicle.get('currency')}",
        f"Doors: {vehicle.get('doors')}",
        f"Seats: {vehicle.get('seats')}",
        f"Storage: {vehicle.get('storageCapacity')} {vehicle.get('storageCapacityUnit')}",
        f"Optional extras: {', '.join(vehicle.get('optionalExtras') or [])}",
        f"Details: {vehicle.get('details')}",
    ]
    return _clean_text("\n".join(str(field) for field in fields if field))


def _vehicle_documents():
    api_base = current_app.config["KABISA_API_BASE_URL"].rstrip("/")
    country = current_app.config["KABISA_COUNTRY"].upper()
    response = requests.get(f"{api_base}/api/client/shop-vehicles?country=rw", timeout=30)
    response.raise_for_status()
    payload = response.json()

    vehicles = payload.get("data", {}).get("vehicles", [])
    documents = []
    for vehicle in vehicles:
        if vehicle.get("country") != country:
            continue

        vehicle_name = f"{vehicle.get('year')} {vehicle.get('make')} {vehicle.get('model')}"
        image_urls = []
        for key in ("mainImage", "orderImage"):
            if vehicle.get(key):
                image_urls.append(vehicle[key])
        image_urls.extend(vehicle.get("additionalImages") or [])
        image_urls.extend(
            color["imageUrl"]
            for color in vehicle.get("availableColors") or []
            if color.get("imageUrl")
        )

        metadata = {
            "source": "gokabisa_vehicle_api",
            "source_url": f"{current_app.config['KABISA_SITE_BASE_URL'].rstrip('/')}/shop/{vehicle.get('shopId')}",
            "country": country,
            "content_type": "vehicle",
            "vehicle_id": vehicle.get("id"),
            "shop_id": vehicle.get("shopId"),
            "make": vehicle.get("make"),
            "model": vehicle.get("model"),
            "classification": vehicle.get("classification"),
            "price": vehicle.get("price"),
            "currency": vehicle.get("currency"),
            "image_urls": image_urls,
        }

        documents.append(
            {
                "id": _stable_id(f"vehicle:{vehicle.get('id')}"),
                "text": _vehicle_text(vehicle),
                "metadata": metadata,
            }
        )

        for index, image_url in enumerate(image_urls):
            documents.append(
                {
                    "id": _stable_id(f"vehicle-image:{vehicle.get('id')}:{image_url}"),
                    "text": _clean_text(
                        f"Image of {vehicle_name}. "
                        f"Classification: {vehicle.get('classification')}. "
                        f"Range: {vehicle.get('range')} km. "
                        f"Battery: {vehicle.get('batteryCapacity')} kWh."
                    ),
                    "metadata": {
                        **metadata,
                        "content_type": "vehicle_image",
                        "image_url": image_url,
                        "image_index": index,
                    },
                }
            )
    return documents


def _charger_text(properties, latitude, longitude):
    availability = properties.get("availability") or {}
    fields = [
        f"Charging station: {properties.get('name')}",
        f"Address: {properties.get('address')}",
        f"Country: {properties.get('country')}",
        f"Status: {properties.get('operationalStatus') or properties.get('status')}",
        f"Owner: {properties.get('owner')}",
        f"Kabisa charger: {properties.get('isKabisa')}",
        f"Connector: {properties.get('connector')}",
        f"Type: {properties.get('type') or properties.get('category')}",
        f"Power: {properties.get('power')} kW",
        f"Available guns: {availability.get('available')} of {availability.get('total')}",
        f"Latitude: {latitude}",
        f"Longitude: {longitude}",
        f"Google Maps: {_charger_maps_url(properties, latitude, longitude)}",
    ]
    return _clean_text("\n".join(str(field) for field in fields if field and "None" not in str(field)))


def _charger_maps_url(properties, latitude, longitude):
    if properties.get("googleMapLink"):
        return properties["googleMapLink"]
    if latitude is not None and longitude is not None:
        return f"https://www.google.com/maps?q={latitude},{longitude}"
    return None


def _charger_documents():
    api_base = current_app.config["KABISA_API_BASE_URL"].rstrip("/")
    country = current_app.config["KABISA_COUNTRY"].upper()
    response = requests.get(f"{api_base}/api/client/chargers-geojson", timeout=30)
    response.raise_for_status()
    payload = response.json()

    features = payload.get("data", {}).get("geojson", {}).get("features", [])
    documents = []
    for feature in features:
        properties = feature.get("properties") or {}
        if properties.get("country") != country:
            continue

        coordinates = feature.get("geometry", {}).get("coordinates") or []
        longitude = coordinates[0] if len(coordinates) > 0 else None
        latitude = coordinates[1] if len(coordinates) > 1 else None
        charger_id = properties.get("id") or properties.get("kabisaId") or properties.get("name")
        metadata = {
            "source": "gokabisa_chargers_api",
            "source_url": _charger_maps_url(properties, latitude, longitude),
            "country": country,
            "content_type": "charger",
            "charger_id": charger_id,
            "kabisa_id": properties.get("kabisaId"),
            "name": properties.get("name"),
            "address": properties.get("address"),
            "status": properties.get("status"),
            "operational_status": properties.get("operationalStatus"),
            "owner": properties.get("owner"),
            "is_kabisa": properties.get("isKabisa"),
            "connector": properties.get("connector"),
            "power": properties.get("power"),
            "latitude": latitude,
            "longitude": longitude,
            "image_url": properties.get("imageUrl"),
        }
        documents.append(
            {
                "id": _stable_id(f"charger:{charger_id}"),
                "text": _charger_text(properties, latitude, longitude),
                "metadata": metadata,
            }
        )
    return documents


def collect_kabisa_documents():
    return _page_documents() + _vehicle_documents() + _charger_documents()
