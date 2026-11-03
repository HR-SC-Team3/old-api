from datetime import datetime

from pydantic import BaseModel


class ItemAmount(BaseModel):
    """A `{item_id, amount}` line, embedded in orders and transfers."""

    item_id: int
    amount: int


class Warehouse(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int
    code: str
    name: str
    address: str
    city: str
    zip_code: str
    province: str
    country: str
    contact_name: str
    contact_phone: str
    contact_email: str


class Location(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int
    warehouse_id: int
    code: str
    name: str


class Supplier(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int
    code: str
    name: str
    address: str
    city: str
    zip_code: str
    province: str
    country: str
    contact_name: str
    phone_number: str
    reference: str


class ItemGroup(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int
    name: str
    description: str


class Inventory(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    item_id: int
    location_id: int
    quantity_on_hand: int
    quantity_expected: int
    quantity_ordered: int
    quantity_allocated: int


class Order(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int
    client_id: int
    order_date: datetime
    request_date: datetime
    reference: str
    customer_po_number: str
    order_status: str
    shipping_notes: str | None
    warehouse_id: int
    ship_to_client_id: int
    bill_to_client_id: int
    items: list[ItemAmount]


class Transfer(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int
    reference: str
    from_location_id: int
    to_location_id: int
    transfer_status: str
    items: list[ItemAmount]

class Shipment(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int
    reference: str
    order_id: int
    shipment_date: datetime
    shipment_type: str
    shipment_status: str
    carrier_name: str
    shipping_method: str
    payment_type: str
    
class Client(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int
    name: str
    address: str
    city: str
    zip_code: str
    province: str
    country: str
    contact_name: str
    contact_phone: str
    contact_email: str
    
class ItemType(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int
    name: str
    description: str
    
class Item(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int
    code: str
    description: str
    barcode: str
    model_number: str
    commodity_code: int
    unit_weight: float
    item_line_id: int
    item_group_id: int
    item_type_id: int
    min_purchase_qty: int
    case_size: int
    packaging_type: str
    order_multiple: int
    supplier_id: int
    supplier_sku: str

class ItemLine(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int
    name: str
    description: str
