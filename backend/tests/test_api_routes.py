from fastapi.testclient import TestClient
import pytest

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_search_empty_query():
    response = client.post("/api/search", json={"query": "   ", "pincode": "110006"})
    assert response.status_code == 400


def test_search_missing_or_invalid_pincode():
    # Missing pincode
    res1 = client.post("/api/search", json={"query": "Crocin 650"})
    assert res1.status_code == 422  # Pydantic validation error

    # Invalid pincode format (e.g. 5 digits)
    res2 = client.post("/api/search", json={"query": "Crocin 650", "pincode": "11000"})
    assert res2.status_code == 422

    # Non-numeric pincode
    res3 = client.post("/api/search", json={"query": "Crocin 650", "pincode": "abcdef"})
    assert res3.status_code == 422


def test_search_unknown_medicine_with_pincode():
    response = client.post("/api/search", json={"query": "NonExistentUnknownMed12345", "pincode": "110006"})
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "NonExistentUnknownMed12345"
    assert data["pincode"] == "110006"
    assert data["results"] == []
    assert len(data["warnings"]) > 0
    assert "disclaimer" in data


def test_search_cached_flow_with_pincode():
    from app.services.cache import cache_service

    query = "Crocin 650"
    pincode = "110006"
    mock_payload = {
        "query": query,
        "pincode": pincode,
        "resolved": {
            "brand": "Crocin 650",
            "salts": ["paracetamol"],
            "strength": "650 mg",
            "form": "tablet",
        },
        "reference_listing": {
            "source": "Tata 1mg",
            "product_name": "Crocin 650mg Tablet",
            "brand": "Crocin",
            "salts": ["paracetamol"],
            "strength": "650 mg",
            "form": "tablet",
            "pack_size_units": 15,
            "price_inr": 32.28,
            "price_per_unit_inr": 2.15,
            "in_stock": True,
            "delivery_pincode": pincode,
            "delivery_info": f"Deliverable to {pincode}",
            "url": "https://www.1mg.com/drugs/crocin-650mg-tablet-90532",
            "fetched_at": "2026-10-19T14:00:00Z",
            "cached": True,
            "is_reference_brand": True,
            "match_confidence": 1.0,
            "flags": [],
        },
        "results": [
            {
                "source": "Tata 1mg",
                "product_name": "Crocin 650mg Tablet",
                "brand": "Crocin",
                "salts": ["paracetamol"],
                "strength": "650 mg",
                "form": "tablet",
                "pack_size_units": 15,
                "price_inr": 32.28,
                "price_per_unit_inr": 2.15,
                "in_stock": True,
                "delivery_pincode": pincode,
                "delivery_info": f"Deliverable to {pincode}",
                "url": "https://www.1mg.com/drugs/crocin-650mg-tablet-90532",
                "fetched_at": "2026-10-19T14:00:00Z",
                "cached": True,
                "is_reference_brand": True,
                "match_confidence": 1.0,
                "flags": [],
            }
        ],
        "savings": {
            "vs_reference_inr_per_unit": 0.0,
            "vs_reference_percent": 0.0,
        },
        "sources": [
            {
                "name": "Tata 1mg",
                "status": "cached",
                "fetched_at": "2026-10-19T14:00:00Z",
                "message": None,
            }
        ],
        "warnings": [],
        "disclaimer": "Prices are indicative. Confirm the medicine, strength and availability with your pharmacist or doctor before buying.",
    }
    cache_service.set_search(query, mock_payload, pincode=pincode)

    response = client.post("/api/search", json={"query": query, "pincode": pincode})
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == query
    assert data["pincode"] == pincode
    assert data["reference_listing"]["price_per_unit_inr"] == 2.15
    assert len(data["results"]) == 1
    assert data["sources"][0]["status"] == "cached"


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Dawa Dost API"
    assert data["status"] == "online"
    assert data["docs"] == "/docs"


def test_cors_headers():
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_search_with_quantity_calculation():
    from app.services.cache import cache_service

    query = "Dolo 650"
    pincode = "110006"
    mock_payload = {
        "query": query,
        "pincode": pincode,
        "resolved": {
            "brand": "Dolo 650",
            "salts": ["paracetamol"],
            "strength": "650 mg",
            "form": "tablet",
        },
        "reference_listing": {
            "source": "Tata 1mg",
            "product_name": "Dolo 650 Tablet",
            "brand": "Micro Labs Ltd",
            "salts": ["paracetamol"],
            "strength": "650 mg",
            "form": "tablet",
            "pack_size_units": 15,
            "price_inr": 34.0,
            "price_per_unit_inr": 2.27,
            "in_stock": True,
            "url": "https://www.1mg.com/drugs/dolo-650",
            "fetched_at": "2026-10-20T10:00:00Z",
            "cached": True,
            "is_reference_brand": True,
            "match_confidence": 1.0,
            "flags": [],
        },
        "results": [
            {
                "source": "Dava India",
                "product_name": "Generic Paracetamol 650mg",
                "brand": "Dava India",
                "salts": ["paracetamol"],
                "strength": "650 mg",
                "form": "tablet",
                "pack_size_units": 10,
                "price_inr": 10.0,
                "price_per_unit_inr": 1.00,
                "in_stock": True,
                "url": "https://www.davaindia.com/paracetamol",
                "fetched_at": "2026-10-20T10:00:00Z",
                "cached": True,
                "is_reference_brand": False,
                "match_confidence": 1.0,
                "flags": [],
            }
        ],
        "savings": {
            "vs_reference_inr_per_unit": 1.27,
            "vs_reference_percent": 55.95,
        },
        "sources": [{"name": "Dava India", "status": "ok", "fetched_at": "2026-10-20T10:00:00Z", "message": None}],
        "warnings": [],
        "disclaimer": "Prices are indicative.",
    }
    cache_service.set_search(query, mock_payload, pincode)

    # Search with quantity = 30 tablets
    res = client.post("/api/search", json={"query": query, "pincode": pincode, "quantity": 30})
    assert res.status_code == 200
    data = res.json()
    assert data["quantity"] == 30
    assert data["savings"]["quantity_requested"] == 30
    # 1.27 * 30 = 38.10
    assert data["savings"]["total_savings_for_quantity_inr"] == 38.10

    # Reference: 2.27 * 30 = 68.10, pack_size 15 -> 2 packs
    ref = data["reference_listing"]
    assert ref["cost_for_quantity_inr"] == 68.10
    assert ref["packs_needed"] == 2

    # Result: 1.00 * 30 = 30.00, pack_size 10 -> 3 packs
    item = data["results"][0]
    assert item["cost_for_quantity_inr"] == 30.00
    assert item["packs_needed"] == 3


