import io
from decimal import Decimal

import httpx
import pytest
from PIL import Image

from app.integrations.product_data import (
    ExternalServiceError,
    OpenFoodFacts,
    ProductSuggestion,
    get_product_data_source,
)
from tests.conftest import category_id, ok

EAN = "4006381333931"
IMG = "https://images.openfoodfacts.org/images/products/400/638/133/3931/front_de.jpg"


def _jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (300, 200), (10, 120, 200)).save(buf, "JPEG")
    return buf.getvalue()


def off_client(product: dict | None, status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "images.openfoodfacts.org":
            return httpx.Response(200, content=_jpeg())
        assert "fields" in request.url.params
        if product is None:
            return httpx.Response(status, json={"status": 0})
        return httpx.Response(status, json={"status": 1, "product": product})

    return httpx.Client(transport=httpx.MockTransport(handler))


# ------------------------------------------------------------------ Adapter


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ({"product_quantity": "1000", "product_quantity_unit": "g"}, ("g", Decimal(1000), "g")),
        ({"product_quantity": 1, "product_quantity_unit": "kg"}, ("g", Decimal(1), "kg")),
        ({"product_quantity": "1.5", "product_quantity_unit": "l"}, ("ml", Decimal("1.5"), "l")),
        ({"product_quantity": "33", "product_quantity_unit": "cl"}, ("ml", Decimal(330), "ml")),
        ({"quantity": "500 g"}, ("g", Decimal(500), "g")),
        ({"product_quantity": 400, "product_quantity_unit": "g"}, ("g", Decimal(400), "g")),
        ({"quantity": "0,7 l"}, ("ml", Decimal("0.7"), "l")),
        ({"quantity": "6 Stück"}, ("piece", None, None)),
        ({}, ("piece", None, None)),
    ],
)
def test_off_quantity_parsing(fields, expected):
    s = OpenFoodFacts(off_client({"product_name": "X", **fields}), "https://off.test").lookup(EAN)
    assert (s.base_unit, s.package_quantity, s.package_unit) == expected


def test_off_mapping():
    s = OpenFoodFacts(
        off_client(
            {
                "product_name": "Sugar",
                "product_name_de": "Zucker",
                "brands": "Südzucker, Other",
                "categories_tags": ["en:sweeteners", "en:sugars"],
                "image_front_url": IMG,
                "product_quantity": "1000",
                "product_quantity_unit": "g",
            }
        ),
        "https://off.test",
    ).lookup(EAN)
    assert (s.name, s.brand, s.category_hint, s.image_url) == (
        "Zucker",
        "Südzucker",
        "Süßwaren",
        IMG,
    )
    assert s.source == "Open Food Facts"


def test_off_unknown_and_errors():
    assert OpenFoodFacts(off_client(None), "https://off.test").lookup(EAN) is None
    assert OpenFoodFacts(off_client(None, status=404), "https://off.test").lookup(EAN) is None
    with pytest.raises(ExternalServiceError):
        OpenFoodFacts(off_client({"x": 1}, status=500), "https://off.test").lookup(EAN)

    def boom(request):
        raise httpx.ConnectTimeout("timeout")

    client = httpx.Client(transport=httpx.MockTransport(boom))
    with pytest.raises(ExternalServiceError):
        OpenFoodFacts(client, "https://off.test").lookup(EAN)


def test_off_image_host_allowlist():
    off = OpenFoodFacts(off_client({}), "https://off.test")
    with pytest.raises(ExternalServiceError):
        off.fetch_image("https://evil.example/x.jpg")
    with pytest.raises(ExternalServiceError):
        off.fetch_image("http://images.openfoodfacts.org/x.jpg")
    assert off.fetch_image(IMG)[:2] == b"\xff\xd8"
    s = OpenFoodFacts(
        off_client({"product_name": "X", "image_front_url": "https://evil.example/x.jpg"}),
        "https://off.test",
    ).lookup(EAN)
    assert s.image_url is None


# ------------------------------------------------------------------ API


class FakeSource:
    name = "Testquelle"
    license = "Testlizenz"

    def __init__(self, suggestion=None, error=False):
        self.suggestion, self.error, self.calls = suggestion, error, []

    def lookup(self, barcode):
        self.calls.append(barcode)
        if self.error:
            raise ExternalServiceError
        return self.suggestion

    def fetch_image(self, url):
        return _jpeg()


@pytest.fixture
def fake(app):
    source = FakeSource(
        ProductSuggestion(
            source="Testquelle",
            source_url="https://example.org",
            license="Testlizenz",
            barcode=EAN,
            name="Zucker",
            brand="Südzucker",
            base_unit="g",
            package_quantity=Decimal(1),
            package_unit="kg",
            category_hint="Süßwaren",
            image_url=IMG,
        )
    )
    app.dependency_overrides[get_product_data_source] = lambda: source
    yield source
    app.dependency_overrides.clear()


def test_disabled_by_default_no_external_call(member_client, fake):
    r = member_client.get(f"/api/v1/product-data/barcode/{EAN}")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "external_disabled"
    assert fake.calls == []


def test_only_admin_can_enable(member_client, admin_client):
    assert ok(member_client.get("/api/v1/settings"))["external_product_data"] is False
    assert (
        member_client.patch("/api/v1/settings", json={"external_product_data": True}).status_code
        == 403
    )
    s = ok(admin_client.patch("/api/v1/settings", json={"external_product_data": True}))
    assert s == {
        "external_product_data": True,
        "expiry_warning_days": 7,
        "stock_warning_factor": 1.25,
    }


def test_lookup_maps_category(admin_client, fake):
    admin_client.patch("/api/v1/settings", json={"external_product_data": True})
    s = ok(admin_client.get(f"/api/v1/product-data/barcode/{EAN}"))
    assert s["name"] == "Zucker"
    assert s["category_id"] == category_id(admin_client, "Süßwaren")
    assert fake.calls == [EAN]


def test_lookup_not_found_and_unavailable(admin_client, fake):
    admin_client.patch("/api/v1/settings", json={"external_product_data": True})
    fake.suggestion = None
    r = admin_client.get(f"/api/v1/product-data/barcode/{EAN}")
    assert (r.status_code, r.json()["error"]["code"]) == (404, "external_not_found")
    fake.error = True
    r = admin_client.get(f"/api/v1/product-data/barcode/{EAN}")
    assert (r.status_code, r.json()["error"]["code"]) == (502, "external_unavailable")
    # Manuelle Anlage funktioniert unabhängig davon (Spez. 11.8)
    r = admin_client.post(
        "/api/v1/products",
        json={"name": "Manuell", "category_id": category_id(admin_client), "base_unit": "g"},
    )
    assert r.status_code == 201


def test_create_with_external_image(admin_client, fake):
    admin_client.patch("/api/v1/settings", json={"external_product_data": True})
    p = ok(
        admin_client.post(
            "/api/v1/products",
            json={
                "name": "Zucker",
                "category_id": category_id(admin_client, "Süßwaren"),
                "base_unit": "g",
                "external_image_url": IMG,
                "variants": [{"package_quantity": 1, "package_unit": "kg", "barcode": EAN}],
            },
        ),
        201,
    )
    assert p["has_image"] is True
    assert p["image_source"] == "Testquelle (Testlizenz)"
    assert admin_client.get(f"/api/v1/products/{p['id']}/image").status_code == 200


def test_external_image_ignored_when_disabled(admin_client, fake):
    p = ok(
        admin_client.post(
            "/api/v1/products",
            json={
                "name": "Zucker",
                "category_id": category_id(admin_client),
                "base_unit": "g",
                "external_image_url": IMG,
            },
        ),
        201,
    )
    assert p["has_image"] is False


def test_image_proxy(admin_client, fake):
    r = admin_client.get("/api/v1/product-data/image", params={"url": IMG})
    assert r.json()["error"]["code"] == "external_disabled"
    admin_client.patch("/api/v1/settings", json={"external_product_data": True})
    r = admin_client.get("/api/v1/product-data/image", params={"url": IMG})
    assert (r.status_code, r.headers["content-type"]) == (200, "image/webp")


def test_no_exponent_notation_and_spreads():
    s = OpenFoodFacts(
        off_client(
            {
                "product_name": "Nutella",
                "product_quantity": 400,
                "product_quantity_unit": "g",
                "categories_tags": ["en:breakfasts", "en:spreads", "en:sweet-spreads"],
            }
        ),
        "https://off.test",
    ).lookup(EAN)
    assert str(s.package_quantity) == "400"
    assert s.category_hint == "Süßwaren"
