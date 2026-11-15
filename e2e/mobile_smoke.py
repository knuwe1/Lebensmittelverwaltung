"""Browser-Durchlauf der mobilen Kernabläufe auf einem simulierten Android-Gerät (Pixel 7):
Einlagern (Barcode, zwei MHD), Entnehmen (FEFO), Entsorgen, Umlagern, Historie mit Storno,
Schutz vor Doppelbuchungen, Restmenge per Waage, Warnungen zu Bestand und Haltbarkeit.

Erwartet einen frisch gestarteten, leeren Stack mit Administrator admin / adminpass123.
Aufruf siehe e2e/README.md.
"""

import re
import sys
import uuid
from datetime import date, timedelta

from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from make_barcode_video import main as make_video  # noqa: E402

BASE = sys.argv[1]
OUT = sys.argv[2]
errors: list[str] = []


def step(name):
    print(f"✓ {name}", flush=True)


def main(pw):
    video = f"{OUT}/barcode.y4m"
    make_video("4006381333931", video)
    browser = pw.chromium.launch(
        args=[
            "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream",
            f"--use-file-for-fake-video-capture={video}",
        ]
    )
    ctx = browser.new_context(**pw.devices["Pixel 7"], ignore_https_errors=True, locale="de-DE")
    ctx.grant_permissions(["camera"])
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on(
        "console",
        lambda m: errors.append(f"console: {m.text}") if m.type == "error" else None,
    )

    # Anmeldung
    page.goto(f"{BASE}/anmelden")
    page.get_by_label("Benutzername").fill("admin")
    page.get_by_label("Passwort").fill("adminpass123")
    page.get_by_role("button", name="Anmelden").click()
    expect(page.get_by_text("Hallo admin")).to_be_visible()
    step("Anmeldung")

    # Stammdaten per API (gleiche Sitzung)
    api = page.request
    cats = api.get(f"{BASE}/api/v1/categories").json()
    cat = next(c["id"] for c in cats if c["name"] == "Milchprodukte")
    kuehl = api.post(f"{BASE}/api/v1/locations", data={"name": "Kühlschrank"}).json()
    api.post(f"{BASE}/api/v1/locations", data={"name": "Vorratsraum"})
    api.post(
        f"{BASE}/api/v1/products",
        data={
            "name": "Testmilch",
            "category_id": cat,
            "base_unit": "ml",
            "default_location_id": kuehl["id"],
            "variants": [{"package_quantity": 1, "package_unit": "l", "barcode": "4006381333931"}],
        },
    )
    step("Stammdaten angelegt")

    # Einlagern über Barcode-Eingabe, zwei Haltbarkeitsdaten
    page.goto(f"{BASE}/einlagern")
    page.get_by_placeholder("Produktname oder Barcode").fill("4006381333931")
    expect(page.get_by_text("Testmilch")).to_be_visible()
    page.get_by_label("Anzahl Packungen").first.fill("1")
    page.get_by_label("Mindestens haltbar bis (MHD)").first.fill("20.11.2027")
    page.keyboard.press("Escape")
    page.get_by_role("button", name="Weiteres Haltbarkeitsdatum").click()
    page.get_by_label("Anzahl Packungen").nth(1).fill("2")
    page.get_by_label("Mindestens haltbar bis (MHD)").nth(1).fill("27.11.2027")
    page.keyboard.press("Escape")
    page.screenshot(path=f"{OUT}/1-einlagern.png", full_page=True)
    page.get_by_role("button", name=re.compile(r"3 l einlagern")).click()
    expect(page.get_by_text(re.compile(r"eingelagert\. Neuer Bestand: 3 l"))).to_be_visible()
    step("Einlagern 3 l mit zwei MHD")

    # Barcode per Kamera scannen (Fake-Kamera zeigt EAN 4006381333931)
    page.get_by_role("button", name="Barcode scannen").click()
    expect(page.get_by_label("Kamerabild")).to_be_visible()
    # Buchungsmaske öffnet sich erst nach erkanntem Barcode
    expect(page.get_by_label("Anzahl Packungen").first).to_be_visible(timeout=20000)
    expect(page.get_by_text("Bestand: 3 l")).to_be_visible()
    page.get_by_role("button", name="Anderes Produkt wählen").click()
    step("Barcode-Scan per Kamera erkennt Testmilch")

    # Entnehmen: automatischer FEFO-Vorschlag
    page.goto(f"{BASE}/entnehmen")
    page.get_by_placeholder("Produktname oder Barcode").fill("Testmilch")
    page.locator("button", has_text="Milchprodukte").first.click()
    expect(page.get_by_text("− 1 l")).to_be_visible()
    page.screenshot(path=f"{OUT}/2-entnehmen.png", full_page=True)
    page.get_by_role("button", name=re.compile(r"1 l entnehmen")).click()
    expect(page.get_by_text(re.compile(r"entnommen\. Neuer Bestand: 2 l"))).to_be_visible()
    step("Entnehmen 1 l (FEFO)")

    stock = api.get(f"{BASE}/api/v1/stock").json()["items"]
    assert [i["expiry_date"] for i in stock] == ["2027-11-27"], stock
    step("FEFO: Position mit früherem MHD wurde reduziert")

    # Schnellentnahme-Liste
    expect(page.get_by_text("Zuletzt entnommen")).to_be_visible()
    step("Zuletzt entnommen angezeigt")

    # Entsorgung
    page.get_by_text("Entsorgung").click()
    page.get_by_placeholder("Produktname oder Barcode").fill("Testmilch")
    page.locator("button", has_text="Milchprodukte").first.click()
    page.get_by_text("Verdorben").click()
    page.get_by_label(re.compile("Menge")).fill("500")
    page.get_by_role("button", name=re.compile(r"500 ml entsorgen")).click()
    expect(page.get_by_text(re.compile(r"entsorgt\. Neuer Bestand: 1,5 l"))).to_be_visible()
    step("Entsorgen 500 ml")

    # Umlagern über Vorratsliste
    page.goto(f"{BASE}/vorraete")
    page.get_by_role("button", name="Umlagern").first.click()
    page.get_by_label("Menge (ml)").fill("1000")
    page.get_by_role("textbox", name="Ziellagerplatz").click()
    page.get_by_role("option", name="Vorratsraum").click()
    page.get_by_role("dialog").get_by_role("button", name="Umlagern").click()
    expect(page.get_by_text(re.compile(r"umgelagert"))).to_be_visible()
    places = sorted(
        (i["location_path"], i["quantity"]) for i in api.get(f"{BASE}/api/v1/stock").json()["items"]
    )
    assert places == [("Kühlschrank", 500), ("Vorratsraum", 1000)], places
    step("Teilumlagerung 1 l")

    # Historie + Storno der Umlagerung
    page.goto(f"{BASE}/historie")
    expect(page.locator(".mantine-Card-root").get_by_text("Umlagerung (Abgang)")).to_be_visible()
    page.screenshot(path=f"{OUT}/3-historie.png", full_page=True)
    page.get_by_role("button", name="Stornieren").first.click()
    page.get_by_role("dialog").get_by_role("button", name="Stornieren").click()
    expect(page.get_by_text("Buchung storniert.")).to_be_visible()
    places = [(i["location_path"], i["quantity"]) for i in api.get(f"{BASE}/api/v1/stock").json()["items"]]
    assert places == [("Kühlschrank", 1500)], places
    step("Storno der Umlagerung")

    # Übersicht und Dashboard rendern
    for path in ["/vorraete?sortierung=expiry", "/lebensmittel", "/lagerplaetze", "/"]:
        page.goto(f"{BASE}{path}")
        page.wait_for_load_state("networkidle")
    page.screenshot(path=f"{OUT}/4-dashboard.png", full_page=True)
    step("Übrige Seiten rendern")

    # Duplikat-Schutz: identischer Key zweimal
    key = str(uuid.uuid4())
    product = api.get(f"{BASE}/api/v1/products?q=Testmilch").json()["items"][0]
    body = {"product_id": product["id"], "quantity": 100}
    for _ in range(2):
        api.post(f"{BASE}/api/v1/stock/consumptions", data=body, headers={"Idempotency-Key": key})
    total = api.get(f"{BASE}/api/v1/products/{product['id']}").json()["stock_quantity"]
    assert total == 1400, total
    step("Doppelte Entnahme-Anfrage nur einmal gebucht")

    # Restmenge per Waage (DEC-029): 3 × 1 kg Zucker, Tüte 5 g
    zucker = api.post(
        f"{BASE}/api/v1/products",
        data={
            "name": "Testzucker",
            "category_id": cat,
            "base_unit": "g",
            "weigh_remaining": True,
            "variants": [{"package_quantity": 1, "package_unit": "kg", "tare_weight": 5}],
        },
    ).json()
    api.post(
        f"{BASE}/api/v1/stock/receipts",
        data={
            "product_id": zucker["id"],
            "variant_id": zucker["variants"][0]["id"],
            "location_id": kuehl["id"],
            "lines": [{"quantity": 3}],
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    for measured, expected_use, expected_total in [("655", "350 g", 2650), ("405", "250 g", 2400)]:
        page.goto(f"{BASE}/entnehmen")
        page.get_by_placeholder("Produktname oder Barcode").fill("Testzucker")
        page.locator("button", has_text="Milchprodukte").first.click()
        expect(page.get_by_text("Restgewicht wiegen")).to_be_visible()
        page.get_by_label("Abgelesenes Gewicht (g)").fill(measured)
        button = page.get_by_role("button", name=f"{expected_use} als Verbrauch buchen")
        expect(button).to_be_enabled()
        if measured == "655":
            page.screenshot(path=f"{OUT}/5-wiegen.png", full_page=True)
        button.click()
        expect(page.get_by_text(re.compile(r"entnommen\. Neuer Bestand"))).to_be_visible()
        total = api.get(f"{BASE}/api/v1/products/{zucker['id']}").json()["stock_quantity"]
        assert total == expected_total, total
    step("Restmenge per Waage: 655 g → 350 g, danach 405 g → 250 g Verbrauch")

    # Phase 5a: Mindestbestand und Haltbarkeit. Joghurt: 2 Stück mit gestern überschrittenem
    # Verbrauchsdatum (physisch da, aber nicht verfügbar) und 1 Stück, MHD in 2 Tagen.
    joghurt = api.post(
        f"{BASE}/api/v1/products",
        data={
            "name": "Testjoghurt",
            "category_id": cat,
            "base_unit": "piece",
            "minimum_stock": 4,
            "target_stock": 8,
        },
    ).json()
    day = lambda n: (date.today() + timedelta(days=n)).isoformat()  # noqa: E731
    api.post(
        f"{BASE}/api/v1/stock/receipts",
        data={
            "product_id": joghurt["id"],
            "location_id": kuehl["id"],
            "lines": [
                {"quantity": 2, "unit": "base", "expiry_type": "use_by", "expiry_date": day(-1)},
                {"quantity": 1, "unit": "base", "expiry_type": "best_before", "expiry_date": day(2)},
            ],
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    page.goto(f"{BASE}/")
    low = page.locator(".mantine-Card-root", has_text="Niedriger Bestand")
    expect(low.get_by_text("Testjoghurt")).to_be_visible()
    expect(low.get_by_text("Mindestbestand unterschritten")).to_be_visible()
    exp = page.locator(".mantine-Card-root", has_text="Alle anzeigen").filter(has_text="Haltbarkeit")
    expect(exp.get_by_text(re.compile("nicht mehr verwenden"))).to_be_visible()
    expect(exp.get_by_text(re.compile(r"in 2 Tagen"))).to_be_visible()
    page.screenshot(path=f"{OUT}/6-dashboard-warnungen.png", full_page=True)
    step("Dashboard warnt vor niedrigem Bestand und Ablauf")

    page.goto(f"{BASE}/haltbarkeit")
    expect(page.get_by_text("Abgelaufen (1)")).to_be_visible()
    expect(page.get_by_text("Bald (1)")).to_be_visible()
    page.screenshot(path=f"{OUT}/7-haltbarkeit.png", full_page=True)
    expired_card = page.locator(".mantine-Card-root", has_text="nicht mehr verwenden")
    # Überschrittenes Verbrauchsdatum: nur Entsorgen anbieten, nicht Entnehmen
    expect(expired_card.get_by_role("button", name="Entnehmen")).to_have_count(0)
    expired_card.get_by_role("button", name="Entsorgen").click()
    expect(page.get_by_role("heading", name="Entsorgen")).to_be_visible()
    page.get_by_role("button", name=re.compile(r"2 Stück entsorgen")).click()
    expect(page.get_by_text(re.compile(r"entsorgt\. Neuer Bestand: 1 Stück"))).to_be_visible()
    step("Abgelaufene Position aus der Haltbarkeitsübersicht entsorgt")

    page.goto(f"{BASE}/haltbarkeit")
    expect(page.get_by_text("Alle (1)")).to_be_visible()
    expect(page.get_by_text("Abgelaufen (0)")).to_be_visible()
    level = next(
        r for r in api.get(f"{BASE}/api/v1/stock/levels").json() if r["product_name"] == "Testjoghurt"
    )
    assert (level["physical_quantity"], level["available_quantity"], level["status"]) == (
        1,
        1,
        "below",
    ), level
    step("Übersicht und Bestandsstatus nach dem Entsorgen aktuell")

    browser.close()


with sync_playwright() as playwright:
    main(playwright)

# Service Worker lässt sich mit dem lokalen Testzertifikat nicht registrieren (erwartet);
# 401 ist die Anmeldeprüfung vor dem Login.
IGNORED = ("favicon", "ServiceWorker", "SSL certificate error", "status of 401")
relevant = [e for e in errors if not any(i in e for i in IGNORED)]
if relevant:
    print("Fehler im Browser:\n" + "\n".join(relevant))
    sys.exit(1)
print("Keine Browserfehler.")
