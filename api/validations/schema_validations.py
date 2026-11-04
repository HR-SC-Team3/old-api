from datetime import datetime

from pydantic import BaseModel, NonNegativeFloat, NonNegativeInt, PositiveInt


class ItemAmount(BaseModel):
    """A `{item_id, amount}` line, embedded in orders and transfers."""

    item_id: PositiveInt
    amount: PositiveInt
    unit_price: NonNegativeFloat | None = None


class Warehouse(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: PositiveInt
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
    id: PositiveInt
    warehouse_id: PositiveInt
    code: str
    name: str


class Supplier(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: PositiveInt
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
    id: PositiveInt
    name: str
    description: str


class Inventory(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    item_id: PositiveInt
    location_id: PositiveInt
    quantity_on_hand: NonNegativeInt
    quantity_expected: NonNegativeInt
    quantity_ordered: NonNegativeInt
    quantity_allocated: NonNegativeInt


class Order(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: PositiveInt
    client_id: PositiveInt
    order_date: datetime
    request_date: datetime
    reference: str
    customer_po_number: str
    order_status: str
    shipping_notes: str | None
    warehouse_id: PositiveInt
    ship_to_client_id: PositiveInt
    bill_to_client_id: PositiveInt
    items: list[ItemAmount]


class Transfer(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: PositiveInt
    reference: str
    from_location_id: PositiveInt
    to_location_id: PositiveInt
    transfer_status: str
    items: list[ItemAmount]

class Shipment(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: PositiveInt
    reference: str
    order_id: PositiveInt
    shipment_date: datetime
    shipment_type: str
    shipment_status: str
    carrier_name: str
    shipping_method: str
    payment_type: str
    items: list[ItemAmount] | None = None
    
class Client(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: PositiveInt
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
    id: PositiveInt
    name: str
    description: str
    
class Item(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: PositiveInt
    code: str
    description: str
    barcode: str
    model_number: str
    commodity_code: int
    unit_weight: NonNegativeFloat
    item_line_id: PositiveInt
    item_group_id: PositiveInt
    item_type_id: PositiveInt
    min_purchase_qty: PositiveInt
    case_size: PositiveInt
    packaging_type: str
    order_multiple: PositiveInt
    supplier_id: PositiveInt
    supplier_sku: str

class ItemLine(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: PositiveInt
    name: str
    description: str
