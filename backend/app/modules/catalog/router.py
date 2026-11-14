import uuid

from fastapi import APIRouter, File, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.core import images
from app.core.errors import NotFoundError
from app.modules.catalog import service
from app.modules.catalog.schemas import (
    BarcodeLookup,
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    ProductCreate,
    ProductOut,
    ProductPage,
    ProductUpdate,
    VariantIn,
    VariantOut,
    VariantUpdate,
)

categories = APIRouter(prefix="/categories", tags=["Produktgruppen"])
products = APIRouter(prefix="/products", tags=["Lebensmittel"])


# ------------------------------------------------------------------ Kategorien


@categories.get("", response_model=list[CategoryOut])
def list_categories(db: DbSession, user: CurrentUser, include_inactive: bool = False):
    return service.list_categories(db, user.household_id, include_inactive)


@categories.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(data: CategoryCreate, db: DbSession, admin: AdminUser):
    cat = service.create_category(db, admin.household_id, data)
    db.commit()
    return cat


@categories.patch("/{category_id}", response_model=CategoryOut)
def update_category(category_id: uuid.UUID, data: CategoryUpdate, db: DbSession, admin: AdminUser):
    cat = service.update_category(db, admin.household_id, category_id, data)
    db.commit()
    return cat


@categories.delete("/{category_id}")
def delete_category(category_id: uuid.UUID, db: DbSession, admin: AdminUser):
    """Löscht eine ungenutzte Produktgruppe; verwendete Gruppen werden deaktiviert."""
    result = service.delete_category(db, admin.household_id, category_id)
    db.commit()
    return {"result": result}


# ------------------------------------------------------------------ Produkte


@products.get("", response_model=ProductPage)
def search_products(
    db: DbSession,
    user: CurrentUser,
    q: str | None = Query(default=None, description="Teil von Name, Marke oder Barcode"),
    category_id: uuid.UUID | None = None,
    brand: str | None = None,
    barcode: str | None = None,
    location_id: uuid.UUID | None = Query(
        default=None,
        description="Nur Produkte mit Bestand an diesem Lagerplatz (inkl. Unterplätze)",
    ),
    in_stock: bool | None = None,
    include_inactive: bool = False,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    items, total = service.search_products(
        db,
        user.household_id,
        q=q,
        category_id=category_id,
        brand=brand,
        barcode=barcode,
        location_id=location_id,
        in_stock=in_stock,
        include_inactive=include_inactive,
        limit=limit,
        offset=offset,
    )
    return ProductPage(items=items, total=total)


@products.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(data: ProductCreate, db: DbSession, user: CurrentUser):
    """Legt ein Produkt an. Alle Benutzer dürfen unbekannte Lebensmittel erfassen (Spez. 3.1);
    Mindest- und Zielbestände dürfen nur Administratoren festlegen."""
    product = service.create_product(db, user, data)
    db.commit()
    return service.product_out(db, product)


@products.get("/barcode/{code}", response_model=BarcodeLookup)
def lookup_barcode(code: str, db: DbSession, user: CurrentUser):
    """Sucht ein Produkt anhand eines Barcodes. Unbekannt → 404 `barcode_unknown`."""
    product, variant = service.lookup_barcode(db, user.household_id, code)
    return BarcodeLookup(product=service.product_out(db, product), variant_id=variant.id)


@products.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: uuid.UUID, db: DbSession, user: CurrentUser):
    return service.product_out(db, service.get_product(db, user.household_id, product_id))


@products.patch("/{product_id}", response_model=ProductOut)
def update_product(product_id: uuid.UUID, data: ProductUpdate, db: DbSession, admin: AdminUser):
    product = service.update_product(db, admin.household_id, product_id, data)
    db.commit()
    return service.product_out(db, product)


@products.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: uuid.UUID, db: DbSession, admin: AdminUser):
    product = service.get_product(db, admin.household_id, product_id)
    image = product.image_path
    service.delete_product(db, admin.household_id, product_id)
    db.commit()
    images.delete_image(image)


@products.post(
    "/{product_id}/variants", response_model=VariantOut, status_code=status.HTTP_201_CREATED
)
def add_variant(product_id: uuid.UUID, data: VariantIn, db: DbSession, user: CurrentUser):
    """Fügt eine Verpackungsvariante hinzu – z. B. um einen neu gescannten Barcode einem
    vorhandenen Produkt zuzuordnen (AC-002)."""
    variant = service.add_variant(db, user.household_id, product_id, data)
    db.commit()
    return variant


@products.patch("/{product_id}/variants/{variant_id}", response_model=VariantOut)
def update_variant(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    data: VariantUpdate,
    db: DbSession,
    admin: AdminUser,
):
    variant = service.update_variant(db, admin.household_id, product_id, variant_id, data)
    db.commit()
    return variant


@products.delete("/{product_id}/variants/{variant_id}")
def remove_variant(product_id: uuid.UUID, variant_id: uuid.UUID, db: DbSession, admin: AdminUser):
    result = service.remove_variant(db, admin.household_id, product_id, variant_id)
    db.commit()
    return {"result": result}


@products.put("/{product_id}/image", response_model=ProductOut)
async def upload_image(
    product_id: uuid.UUID, db: DbSession, user: CurrentUser, file: UploadFile = File(...)
):
    product = service.get_product(db, user.household_id, product_id)
    data = await file.read()
    new_path = images.save_image(data, "products")
    old_path, product.image_path, product.image_source = product.image_path, new_path, None
    db.commit()
    images.delete_image(old_path)
    return service.product_out(db, product)


@products.get("/{product_id}/image", response_class=FileResponse)
def get_image(product_id: uuid.UUID, db: DbSession, user: CurrentUser):
    product = service.get_product(db, user.household_id, product_id)
    if not product.image_path:
        raise NotFoundError("Kein Produktbild vorhanden.", code="image_not_found")
    path = images.resolve(product.image_path)
    if not path.exists():
        raise NotFoundError("Kein Produktbild vorhanden.", code="image_not_found")
    return FileResponse(
        path, media_type="image/webp", headers={"Cache-Control": "private, max-age=86400"}
    )


@products.delete("/{product_id}/image", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(product_id: uuid.UUID, db: DbSession, admin: AdminUser):
    product = service.get_product(db, admin.household_id, product_id)
    old_path, product.image_path = product.image_path, None
    db.commit()
    images.delete_image(old_path)
