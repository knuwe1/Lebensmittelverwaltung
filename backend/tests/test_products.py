import io

from PIL import Image

from tests.conftest import category_id, make_location, make_product, ok, receive

EAN = "4006381333931"


def test_create_minimal_product_with_variants(member_client):
    p = make_product(
        member_client,
        name="Zucker",
        base_unit="g",
        variants=[
            {"package_quantity": 500, "package_unit": "g", "barcode": "96385074"},
            {"package_quantity": 1, "package_unit": "kg", "barcode": EAN, "is_default": True},
        ],
    )
    assert p["base_unit"] == "g"
    assert p["category_name"] == "Milchprodukte"
    by_code = {v["barcode"]: v for v in p["variants"]}
    assert by_code[EAN]["base_quantity"] == 1000
    assert by_code[EAN]["is_default"] is True
    assert by_code["96385074"]["is_default"] is False


def test_single_default_variant_is_chosen_automatically(admin_client):
    p = make_product(admin_client, variants=[{"package_quantity": 1, "package_unit": "l"}])
    assert p["variants"][0]["is_default"] is True


def test_incompatible_variant_unit_rejected(admin_client):
    r = admin_client.post(
        "/api/v1/products",
        json={
            "name": "Milch",
            "category_id": category_id(admin_client),
            "base_unit": "ml",
            "variants": [{"package_quantity": 1, "package_unit": "kg"}],
        },
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "incompatible_unit"


def test_barcode_unique_and_lookup(admin_client):
    p = make_product(
        admin_client, variants=[{"package_quantity": 1, "package_unit": "l", "barcode": EAN}]
    )
    r = admin_client.post(
        "/api/v1/products",
        json={
            "name": "Andere Milch",
            "category_id": category_id(admin_client),
            "base_unit": "ml",
            "variants": [{"package_quantity": 1, "package_unit": "l", "barcode": EAN}],
        },
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "barcode_taken"

    found = ok(admin_client.get(f"/api/v1/products/barcode/{EAN}"))
    assert found["product"]["id"] == p["id"]
    assert found["variant_id"] == p["variants"][0]["id"]

    r = admin_client.get("/api/v1/products/barcode/96385074")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "barcode_unknown"


def test_upc_a_finds_ean13(admin_client):
    make_product(
        admin_client,
        variants=[{"package_quantity": 1, "package_unit": "l", "barcode": "036000291452"}],
    )
    assert admin_client.get("/api/v1/products/barcode/0036000291452").status_code == 200
    assert admin_client.get("/api/v1/products/barcode/036000291452").status_code == 200


def test_add_scanned_barcode_to_existing_product(member_client):
    p = make_product(member_client)
    v = ok(
        member_client.post(
            f"/api/v1/products/{p['id']}/variants",
            json={"package_quantity": 500, "package_unit": "ml", "barcode": EAN},
        ),
        201,
    )
    assert v["base_quantity"] == 500
    assert ok(member_client.get(f"/api/v1/products/barcode/{EAN}"))["product"]["id"] == p["id"]


def test_search(admin_client):
    make_product(admin_client, name="Vollmilch", brand="Weihenstephan")
    make_product(
        admin_client,
        name="Zucker",
        base_unit="g",
        variants=[{"package_quantity": 1, "package_unit": "kg", "barcode": EAN}],
    )

    def names(params):
        return [p["name"] for p in ok(admin_client.get("/api/v1/products", params=params))["items"]]

    assert names({"q": "milch"}) == ["Vollmilch"]
    assert names({"q": "stephan"}) == ["Vollmilch"]
    assert names({"q": "4006381"}) == ["Zucker"]
    assert names({"barcode": EAN}) == ["Zucker"]
    assert names({"category_id": category_id(admin_client, "Gewürze")}) == []
    assert names({"in_stock": True}) == []


def test_stock_levels_admin_only_and_validated(admin_client, member_client):
    r = member_client.post(
        "/api/v1/products",
        json={
            "name": "X",
            "category_id": category_id(member_client),
            "base_unit": "g",
            "minimum_stock": 100,
        },
    )
    assert r.status_code == 403
    p = make_product(admin_client, minimum_stock=2000, target_stock=6000)
    assert (p["minimum_stock"], p["target_stock"]) == (2000, 6000)
    r = admin_client.patch(f"/api/v1/products/{p['id']}", json={"target_stock": 1000})
    assert r.json()["error"]["code"] == "target_below_minimum"
    # Mindestbestand entfernen = keine Überwachung (FR-SHP-001)
    p = ok(admin_client.patch(f"/api/v1/products/{p['id']}", json={"minimum_stock": None}))
    assert p["minimum_stock"] is None and p["target_stock"] == 6000
    assert member_client.patch(f"/api/v1/products/{p['id']}", json={"name": "Y"}).status_code == 403


def test_base_unit_locked_after_stock(admin_client):
    p = make_product(
        admin_client, base_unit="g", variants=[{"package_quantity": 1, "package_unit": "kg"}]
    )
    loc = make_location(admin_client, "Schrank")
    receive(admin_client, p, loc, [{"quantity": 1}], variant_id=p["variants"][0]["id"])
    r = admin_client.patch(f"/api/v1/products/{p['id']}", json={"base_unit": "ml"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "base_unit_locked"


def test_delete_product_only_without_history(admin_client):
    a = make_product(admin_client, name="A")
    b = make_product(admin_client, name="B")
    receive(admin_client, b, make_location(admin_client, "S"), [{"quantity": 1, "unit": "base"}])
    assert admin_client.delete(f"/api/v1/products/{a['id']}").status_code == 204
    r = admin_client.delete(f"/api/v1/products/{b['id']}")
    assert r.json()["error"]["code"] == "product_has_history"
    p = ok(admin_client.patch(f"/api/v1/products/{b['id']}", json={"active": False}))
    assert p["active"] is False
    assert ok(admin_client.get("/api/v1/products"))["total"] == 0


def _png(size=(1600, 900)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 30, 30)).save(buf, "PNG")
    return buf.getvalue()


def test_image_upload_is_reencoded(member_client):
    p = make_product(member_client)
    r = member_client.put(
        f"/api/v1/products/{p['id']}/image", files={"file": ("x.png", _png(), "image/png")}
    )
    assert ok(r)["has_image"] is True
    img = member_client.get(f"/api/v1/products/{p['id']}/image")
    assert img.headers["content-type"] == "image/webp"
    assert max(Image.open(io.BytesIO(img.content)).size) == 1024

    r = member_client.put(
        f"/api/v1/products/{p['id']}/image",
        files={"file": ("x.png", b"<script>alert(1)</script>", "image/png")},
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_image"
