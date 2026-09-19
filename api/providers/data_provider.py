import functools
import os

from models.warehouses import Warehouses
from models.locations import Locations
from models.transfers import Transfers
from models.transfer_items import TransferItems
from models.items import Items
from models.item_lines import ItemLines
from models.item_groups import ItemGroups
from models.item_types import ItemTypes
from models.inventories import Inventories
from models.suppliers import Suppliers
from models.orders import Orders
from models.order_items import OrderItems
from models.clients import Clients
from models.shipments import Shipments
from models.shipment_items import ShipmentItems

DEBUG = False

_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data")
)

ROOT_PATH = _ROOT + os.sep

# Every fetch_X_pool() below used to construct a brand-new model instance
# (re-reading and json.load()-ing the whole data/*.json file) on every single
# call. For collections enriched per-row via another pool (orders/shipments/
# transfers pulling in their *_item pools once per row), that meant re-parsing
# multi-megabyte files thousands of times per request. @singleton_pool makes
# each fetch_X_pool() below build its instance once and reuse it for the life
# of the process, and as a side effect makes POST/PUT/DELETE's mutate-then-save
# calls act on the same instance instead of two independently-reloaded ones.
_reset_callbacks = []


def singleton_pool(factory):
    """Decorator: turn a zero-arg pool factory into a memoized singleton.

    The wrapped function's own cache is what gets cleared by reset_pools(),
    so each fetch_X_pool() below stays a plain one-liner that just describes
    how to build its pool -- the caching behavior lives entirely here.
    """
    cache = {}

    @functools.wraps(factory)
    def wrapper():
        if "instance" not in cache:
            cache["instance"] = factory()
        return cache["instance"]

    _reset_callbacks.append(cache.clear)
    return wrapper


def reset_pools():
    """Test-only: drop every cached pool so the next fetch reloads from disk."""
    for clear in _reset_callbacks:
        clear()


@singleton_pool
def fetch_warehouse_pool():
    return Warehouses(ROOT_PATH, DEBUG)

@singleton_pool
def fetch_location_pool():
    return Locations(ROOT_PATH, DEBUG)

@singleton_pool
def fetch_transfer_pool():
    return Transfers(ROOT_PATH, DEBUG)

@singleton_pool
def fetch_transfer_item_pool():
    return TransferItems(ROOT_PATH, DEBUG)

@singleton_pool
def fetch_item_pool():
    return Items(ROOT_PATH, DEBUG)

@singleton_pool
def fetch_item_line_pool():
    return ItemLines(ROOT_PATH, DEBUG)

@singleton_pool
def fetch_item_group_pool():
    return ItemGroups(ROOT_PATH, DEBUG)

@singleton_pool
def fetch_item_type_pool():
    return ItemTypes(ROOT_PATH, DEBUG)

@singleton_pool
def fetch_inventory_pool():
    return Inventories(ROOT_PATH, DEBUG)

@singleton_pool
def fetch_supplier_pool():
    return Suppliers(ROOT_PATH, DEBUG)

@singleton_pool
def fetch_order_pool():
    return Orders(ROOT_PATH, DEBUG)

@singleton_pool
def fetch_order_item_pool():
    return OrderItems(ROOT_PATH, DEBUG)

@singleton_pool
def fetch_client_pool():
    return Clients(ROOT_PATH, DEBUG)

@singleton_pool
def fetch_shipment_pool():
    return Shipments(ROOT_PATH, DEBUG)

@singleton_pool
def fetch_shipment_item_pool():
    return ShipmentItems(ROOT_PATH, DEBUG)