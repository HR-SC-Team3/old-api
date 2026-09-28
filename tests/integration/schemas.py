"""
Shared pydantic response schemas for the integration test suite.

Field types/requiredness here should match the "documented" shape of each
resource; where the live API's actual behavior diverges (missing fields,
wrong types, etc.), that's exercised with `model_validate` failing inside
an `xfail(strict=True)` test in the relevant resource's test file, not by
loosening the schema itself.
"""

from datetime import datetime

from pydantic import BaseModel


class ItemAmount(BaseModel):
    """A `{item_id, amount}` line, embedded in orders and transfers."""

    item_id: int
    amount: int


class Warehouse(BaseModel):
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
    created_at: datetime
    updated_at: datetime


class Location(BaseModel):
    id: int
    warehouse_id: int
    code: str
    name: str
    created_at: datetime
    updated_at: datetime


class Supplier(BaseModel):
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
    created_at: datetime
    updated_at: datetime


class ItemGroup(BaseModel):
    id: int
    name: str
    description: str
    created_at: datetime
    updated_at: datetime


class Inventory(BaseModel):
    item_id: int
    location_id: int
    quantity_on_hand: int
    quantity_expected: int
    quantity_ordered: int
    quantity_allocated: int
    created_at: datetime
    updated_at: datetime


class Order(BaseModel):
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
    created_at: datetime
    updated_at: datetime
    items: list[ItemAmount]


class Transfer(BaseModel):
    id: int
    reference: str
    from_location_id: int
    to_location_id: int
    transfer_status: str
    created_at: datetime
    updated_at: datetime
    items: list[ItemAmount]
