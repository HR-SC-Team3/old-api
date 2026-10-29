import os
import socketserver
import http.server
import json

from providers import auth_provider
from providers import data_provider

from processors import notification_processor

from typing import Any

### Route Handlers (resources)
from controllers.item_groups import ItemGroups
from controllers.suppliers import Suppliers
from controllers.transfers import Transfers
from controllers.warehouses import Warehouses
from controllers.inventory import Inventory
from controllers.shipment import Shipment

# Enables a test-only cache-reset endpoint (see do_POST below). Never set in
# a normal run of this server -- only the test suite's conftest.py sets it
# when spawning this process.
TEST_MODE = os.environ.get("API_TEST_MODE") == "1"


class ApiRequestHandler(http.server.BaseHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        self.controllers = {
            "item_groups": ItemGroups(),
            "suppliers": Suppliers(),
            "transfers": Transfers(),
            "warehouses": Warehouses(),
        }
        super().__init__(*args, **kwargs)

    def address_string(self):
        # Defensive: force the raw client IP instead of BaseHTTPRequestHandler's
        # default, in case some environment/version makes that do a reverse-DNS
        # lookup. (On this repo's own dev machines this turned out not to be the
        # cause of the ~2s "sometimes slow" tax -- see the "connect to 127.0.0.1,
        # not localhost" note in the README / commit history for the real cause.)
        return self.client_address[0]

    def _drain_request_body(self):
        # Rejecting a request before reading its body leaves those bytes
        # unread in the socket. On this single-threaded, non-keep-alive
        # server, closing the connection while unread bytes are still
        # pending in the kernel receive buffer can trigger a TCP RST
        # instead of a clean close, surfacing as a connection reset on
        # the client. Draining the body before responding avoids that.
        content_length = self.headers.get("Content-Length")
        if content_length:
            self.rfile.read(int(content_length))

    def _deny_without_access(self, user, paths, method) -> bool:
        if auth_provider.has_access(user, paths, method):
            return False
        self._drain_request_body()
        self.send_response(403)
        self.end_headers()
        return True

    def _read_json_body(self):
        content_length = int(self.headers["Content-Length"])
        return json.loads(self.rfile.read(content_length).decode())

    def send_json_response(self, status_code: int, data: Any):
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_GET(self):
        api_key = self.headers.get("API_KEY")
        user = auth_provider.get_user(api_key)
        if user == None:
            self._drain_request_body()
            self.send_response(401)
            self.end_headers()
            return
        else:
            try:
                paths = self.path.split("/")
                if len(paths) > 3 and paths[1] == "api" and paths[2] == "v1":

                    # Strip out the query parameters, if any. We do not support any query parameters, so we just ignore them.
                    paths[3] = paths[3].split("?")[0]
                    match paths[3]:
                        case "warehouses" | "suppliers" | "item_groups" | "transfers":
                            if self._deny_without_access(user, paths[3:], "get"):
                                return
                            controller = self.controllers[paths[3]]
                            match len(paths) - 3:
                                case 1:
                                    self.send_json_response(200, controller.get())
                                case 2:
                                    resource = controller.get(int(paths[4]))
                                    if resource is None:
                                        self.send_response(404)
                                        self.end_headers()
                                    else:
                                        self.send_json_response(200, resource)
                                case 3 if paths[5] == controller.sub_resource:
                                    self.send_json_response(
                                        200, controller.get_sub_resource(int(paths[4]))
                                    )
                                case _:
                                    self.send_response(404)
                                    self.end_headers()
                        case "inventories":
                            if self._deny_without_access(user, paths[3:], "get"):
                                return
                            match len(paths) - 3:
                                case 1:
                                    self.send_json_response(200, self.inventory_controller.get())
                                case 2:
                                    self.send_response(404)
                                    self.end_headers()
                                case 3 if paths[5] == "totals":
                                    item_id = int(paths[4])
                                    self.send_json_response(200, self.inventory_controller.get_totals(item_id))
                                case 3:
                                    item_id = int(paths[4])
                                    location_id = int(paths[5])
                                    inventory = self.inventory_controller.get(item_id, location_id)
                                    if inventory is None:
                                        self.send_response(404)
                                        self.end_headers()
                                    else:
                                        self.send_json_response(200, inventory)
                                case _:
                                    self.send_response(404)
                                    self.end_headers()
                        case "shipments":
                            if self._deny_without_access(user, paths[3:], "get"):
                                return
                            match len(paths) - 3:
                                case 1:
                                    self.send_json_response(200, self.shipment_controller.get())
                                case 2:
                                    shipment = self.shipment_controller.get(int(paths[4]))
                                    if shipment is None:
                                        self.send_response(404)
                                        self.end_headers()
                                    else:
                                        self.send_json_response(200, shipment)
                                case 3 if paths[5] == "orders":
                                    self.send_json_response(200, self.shipment_controller.get_orders(int(paths[4])))
                                case 3 if paths[5] == "items":
                                    self.send_json_response(200, self.shipment_controller.get_items(int(paths[4])))
                                case _:
                                    self.send_response(404)
                                    self.end_headers()
                        case _:
                            self.handle_get_version_1(paths[3:], user)
            except ValueError:
                self.send_response(400)
                self.end_headers()
            except Exception:
                self.send_response(500)
                self.end_headers()

    def do_PUT(self):
        api_key = self.headers.get("API_KEY")
        user = auth_provider.get_user(api_key)
        if user == None:
            self._drain_request_body()
            self.send_response(401)
            self.end_headers()
        else:
            try:
                paths = self.path.split("/")
                if len(paths) > 3 and paths[1] == "api" and paths[2] == "v1":
                    match paths[3]:
                        case "transfers":
                            if self._deny_without_access(user, paths[3:], "put"):
                                return
                            controller = self.controllers["transfers"]
                            match len(paths) - 3:
                                case 2:
                                    transfer_id = int(paths[4])
                                    updated_transfer = self._read_json_body()
                                    if controller.put(transfer_id, updated_transfer) is None:
                                        self.send_response(404)
                                    else:
                                        self.send_response(200)
                                    self.end_headers()
                                case 3 if paths[5] == "commit":
                                    controller.commit(int(paths[4]))
                                    self.send_response(200)
                                    self.end_headers()
                                case _:
                                    self.send_response(404)
                                    self.end_headers()
                        case "warehouses" | "suppliers" | "item_groups":
                            if self._deny_without_access(user, paths[3:], "put"):
                                return
                            resource_id = int(paths[4])
                            updated_resource = self._read_json_body()
                            if (
                                self.controllers[paths[3]].put(
                                    resource_id, updated_resource
                                )
                                is None
                            ):
                                self.send_response(404)
                            else:
                                self.send_response(200)
                            self.end_headers()
                        case "inventories":
                            if self._deny_without_access(user, paths[3:], "put"):
                                return
                            if len(paths) != 6:
                                self.send_response(404)
                                self.end_headers()
                                return
                            item_id = int(paths[4])
                            location_id = int(paths[5])
                            updated_inventory = self._read_json_body()
                            if self.inventory_controller.put(item_id, location_id, updated_inventory) is None:
                                self.send_response(404)
                            else:
                                self.send_response(200)
                            self.end_headers()
                        case "shipments":
                            if self._deny_without_access(user, paths[3:], "put"):
                                return
                            match len(paths) - 3:
                                case 2:
                                    shipment_id = int(paths[4])
                                    update_shipment = self._read_json_body()
                                    if self.shipment_controller.put(update_shipment, shipment_id) is None:
                                        self.send_response(404)
                                    else:
                                        self.send_response(200)
                                    self.end_headers()
                                case 3 if (paths[5]) == "orders":
                                    shipment_id = int(paths[4])
                                    updated_orders = self._read_json_body()
                                    if self.shipment_controller.put_orders(shipment_id, updated_orders) is None:
                                        self.send_response(404)
                                    else:
                                        self.send_response(200)
                                    self.end_headers()
                                case 3 if (paths[5]) =="items":
                                    shipment_id = int(paths[4])
                                    updated_orders = self._read_json_body()
                                    if self.shipment_controller.put_items(shipment_id, updated_orders) is None:
                                        self.send_response(404)
                                    else:
                                        self.send_response(200)
                                    self.end_headers()
                                case _:
                                    self.send_response(404)
                                    self.end_headers()
                        case _:
                            self.handle_put_version_1(paths[3:], user)
            except ValueError:
                self.send_response(400)
                self.end_headers()
            except Exception:
                self.send_response(500)
                self.end_headers()

    def do_POST(self):
        if TEST_MODE and self.path == "/api/v1/_test/reset-cache":
            data_provider.reset_pools()
            self.send_response(204)
            self.end_headers()
            return
        api_key = self.headers.get("API_KEY")
        user = auth_provider.get_user(api_key)
        if user == None:
            self._drain_request_body()
            self.send_response(401)
            self.end_headers()
            return
        else:
            try:
                paths = self.path.split("/")
                if len(paths) > 3 and paths[1] == "api" and paths[2] == "v1":
                    match paths[3]:
                        case "warehouses" | "suppliers" | "item_groups" | "transfers":
                            if self._deny_without_access(user, paths[3:], "post"):
                                return
                            media_type = (
                                self.headers.get("Content-Type", "")
                                .split(";", 1)[0]
                                .strip()
                                .lower()
                            )
                            if media_type != "application/json":
                                self._drain_request_body()
                                self.send_response(415)
                                self.end_headers()
                                return
                            self.controllers[paths[3]].post(self._read_json_body())
                            self.send_response(201)
                            self.end_headers()
                        case "inventories":
                            if self._deny_without_access(user, paths[3:], "post"):
                                return
                            media_type = (self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower())
                            if media_type != "application/json":
                                self._drain_request_body()
                                self.send_response(415)
                                self.end_headers()
                                return
                            new_inventory = self._read_json_body()
                            required_fields = [ "item_id", "location_id", "quantity_on_hand", "quantity_expected", "quantity_ordered", "quantity_allocated",]
                            if not all(field in new_inventory for field in required_fields):
                                self.send_response(400)
                                self.end_headers()
                                return
                            self.inventory_controller.post(new_inventory)
                            self.send_response(201)
                            self.end_headers()
                        case "shipments":
                            if self._deny_without_access(user, paths[3:], "post"):
                                return
                            media_type = (self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower())
                            if media_type != "application/json":
                                self._drain_request_body()
                                self.send_response(415)
                                self.end_headers()
                                return
                            new_shipment = self._read_json_body()
                            if not isinstance(new_shipment, dict):
                                self.send_response(400)
                                self.end_headers()
                                return
                            required_fields = [ "reference", "order_id", "shipment_date", "shipment_type", "shipment_status", "carrier_name", "shipping_method", "payment_type",]
                            if not all(field in new_shipment for field in required_fields):
                                self.send_response(400)
                                self.end_headers()
                                return
                            created_shipment = self.shipment_controller.post(new_shipment)
                            if created_shipment is None:
                                self.send_response(201)
                                self.end_headers()
                            else:
                                self.send_json_response(201, created_shipment)
                        case _:
                            self.handle_post_version_1(paths[3:], user)
            except Exception:
                self.send_response(500)
                self.end_headers()

    def do_DELETE(self):
        api_key = self.headers.get("API_KEY")
        user = auth_provider.get_user(api_key)
        if user == None:
            self._drain_request_body()
            self.send_response(401)
            self.end_headers()
        else:
            try:
                paths = self.path.split("/")
                if len(paths) > 3 and paths[1] == "api" and paths[2] == "v1":
                    match paths[3]:
                        case "warehouses" | "suppliers" | "item_groups" | "transfers":
                            if self._deny_without_access(user, paths[3:], "delete"):
                                return
                            if self.controllers[paths[3]].delete(int(paths[4])) is None:
                                self.send_response(404)
                            else:
                                self.send_response(200)
                            self.end_headers()
                        case _:
                            self.handle_delete_version_1(paths[3:], user)
            except ValueError:
                self.send_response(400)
                self.end_headers()
            except Exception:
                self.send_response(500)
                self.end_headers()

    # region Old Shit
    def handle_get_version_1(self, paths, user):
        # Strip out the query parameters, if any. We do not support any query parameters, so we just ignore them.
        paths[0] = paths[0].split("?")[0]

        if not auth_provider.has_access(user, paths, "get"):
            self._drain_request_body()
            self.send_response(403)
            self.end_headers()
            return
        if paths[0] == "locations":
            parts = len(paths)
            match parts:
                case 1:
                    locations = data_provider.fetch_location_pool().get_locations()
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(locations).encode("utf-8"))
                case 2:
                    location_id = int(paths[1])
                    location = data_provider.fetch_location_pool().get_location(
                        location_id
                    )
                    if location is None:
                        self.send_response(404)
                        self.end_headers()
                        return
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(location).encode("utf-8"))
                case _:
                    self.send_response(404)
                    self.end_headers()
        elif paths[0] == "items":
            parts = len(paths)
            match parts:
                case 1:
                    items = data_provider.fetch_item_pool().get_items()
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(items).encode("utf-8"))
                case 2:
                    item_id = int(paths[1])
                    item = data_provider.fetch_item_pool().get_item(item_id)
                    if item is None:
                        self.send_response(404)
                        self.end_headers()
                        return
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(item).encode("utf-8"))
                case 3:
                    if paths[2] == "inventory":
                        item_id = int(paths[1])
                        inventories = data_provider.fetch_inventory_pool().get_inventories_for_item(
                            item_id
                        )
                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(inventories).encode("utf-8"))
                    else:
                        self.send_response(404)
                        self.end_headers()
                case 4:
                    if paths[2] == "inventory" and paths[3] == "totals":
                        item_id = int(paths[1])
                        totals = data_provider.fetch_inventory_pool().get_inventory_totals_for_item(
                            item_id
                        )
                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(totals).encode("utf-8"))
                    else:
                        self.send_response(404)
                        self.end_headers()
                case _:
                    self.send_response(404)
                    self.end_headers()
        elif paths[0] == "item_lines":
            parts = len(paths)
            match parts:
                case 1:
                    item_lines = data_provider.fetch_item_line_pool().get_item_lines()
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(item_lines).encode("utf-8"))
                case 2:
                    item_line_id = int(paths[1])
                    item_line = data_provider.fetch_item_line_pool().get_item_line(
                        item_line_id
                    )
                    item_line = data_provider.fetch_item_line_pool().get_item_line(
                        item_line_id
                    )
                    if item_line is None:
                        self.send_response(404)
                        self.end_headers()
                        return
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(item_line).encode("utf-8"))
                case 3:
                    if paths[2] == "items":
                        item_line_id = int(paths[1])
                        items = data_provider.fetch_item_pool().get_items_for_item_line(
                            item_line_id
                        )
                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(items).encode("utf-8"))
                    else:
                        self.send_response(404)
                        self.end_headers()
                case _:
                    self.send_response(404)
                    self.end_headers()
        elif paths[0] == "item_types":
            parts = len(paths)
            match parts:
                case 1:
                    item_types = data_provider.fetch_item_type_pool().get_item_types()
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(item_types).encode("utf-8"))
                case 2:
                    item_type_id = int(paths[1])
                    item_type = data_provider.fetch_item_type_pool().get_item_type(
                        item_type_id
                    )
                    item_type = data_provider.fetch_item_type_pool().get_item_type(
                        item_type_id
                    )
                    if item_type is None:
                        self.send_response(404)
                        self.end_headers()
                        return
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(item_type).encode("utf-8"))
                case 3:
                    if paths[2] == "items":
                        item_type_id = int(paths[1])
                        items = data_provider.fetch_item_pool().get_items_for_item_type(
                            item_type_id
                        )
                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(items).encode("utf-8"))
                    else:
                        self.send_response(404)
                        self.end_headers()
                case _:
                    self.send_response(404)
                    self.end_headers()
        elif paths[0] == "inventories":
            parts = len(paths)
            match parts:
                case 1:
                    inventories = data_provider.fetch_inventory_pool().get_inventories()
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(inventories).encode("utf-8"))
                case 2:
                    # Inventory rows are keyed on a composite (item_id, location_id)
                    # in the new schema, so a single surrogate id has no meaning.
                    self.send_response(404)
                    self.end_headers()
                case _:
                    self.send_response(404)
                    self.end_headers()
        elif paths[0] == "orders":
            parts = len(paths)
            match parts:
                case 1:
                    orders = data_provider.fetch_order_pool().get_orders()
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(orders).encode("utf-8"))
                case 2:
                    order_id = int(paths[1])
                    order = data_provider.fetch_order_pool().get_order(order_id)
                    if order is None:
                        self.send_response(404)
                        self.end_headers()
                        return
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(order).encode("utf-8"))
                case 3:
                    if paths[2] == "items":
                        order_id = int(paths[1])
                        items = data_provider.fetch_order_pool().get_items_in_order(
                            order_id
                        )
                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(items).encode("utf-8"))
                    else:
                        self.send_response(404)
                        self.end_headers()
                case _:
                    self.send_response(404)
                    self.end_headers()
        elif paths[0] == "clients":
            parts = len(paths)
            match parts:
                case 1:
                    clients = data_provider.fetch_client_pool().get_clients()
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(clients).encode("utf-8"))
                case 2:
                    client_id = int(paths[1])
                    client = data_provider.fetch_client_pool().get_client(client_id)
                    if client is None:
                        self.send_response(404)
                        self.end_headers()
                        return
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(client).encode("utf-8"))
                case 3:
                    if paths[2] == "orders":
                        client_id = int(paths[1])
                        orders = data_provider.fetch_order_pool().get_orders_for_client(
                            client_id
                        )
                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(orders).encode("utf-8"))
                    else:
                        self.send_response(404)
                        self.end_headers()
                case _:
                    self.send_response(404)
                    self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

            self.end_headers()

    def handle_post_version_1(self, paths, user):
        if not auth_provider.has_access(user, paths, "post"):
            self._drain_request_body()
            self.send_response(403)
            self.end_headers()
            return

        content_type = self.headers.get("Content-Type", "")
        media_type = content_type.split(";", 1)[0].strip().lower()

        if media_type != "application/json":
            self._drain_request_body()
            self.send_response(415)
            self.end_headers()
            return
        if paths[0] == "locations":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            new_location = json.loads(post_data.decode())
            data_provider.fetch_location_pool().add_location(new_location)
            data_provider.fetch_location_pool().save()
            self.send_response(201)
            self.end_headers()
        elif paths[0] == "items":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            new_item = json.loads(post_data.decode())
            data_provider.fetch_item_pool().add_item(new_item)
            data_provider.fetch_item_pool().save()
            self.send_response(201)
            self.end_headers()
        elif paths[0] == "item_lines":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            new_item_line = json.loads(post_data.decode())
            data_provider.fetch_item_line_pool().add_item_line(new_item_line)
            data_provider.fetch_item_line_pool().save()
            self.send_response(201)
            self.end_headers()
        elif paths[0] == "item_types":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            new_item_type = json.loads(post_data.decode())
            data_provider.fetch_item_type_pool().add_item_type(new_item_type)
            data_provider.fetch_item_type_pool().save()
            self.send_response(201)
            self.end_headers()
        elif paths[0] == "inventories":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            new_inventory = json.loads(post_data.decode())

            required_fields = [
                "item_id",
                "location_id",
                "quantity_on_hand",
                "quantity_expected",
                "quantity_ordered",
                "quantity_allocated",
            ]

            if not all(field in new_inventory for field in required_fields):
                self.send_response(400)
                self.end_headers()
                return

            data_provider.fetch_inventory_pool().add_inventory(new_inventory)
            data_provider.fetch_inventory_pool().save()
            self.send_response(201)
            self.end_headers()

        elif paths[0] == "orders":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            new_order = json.loads(post_data.decode())
            data_provider.fetch_order_pool().add_order(new_order)
            data_provider.fetch_order_pool().save()
            self.send_response(201)
            self.end_headers()
        elif paths[0] == "clients":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            new_client = json.loads(post_data.decode())
            data_provider.fetch_client_pool().add_client(new_client)
            data_provider.fetch_client_pool().save()
            self.send_response(201)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
            self.end_headers()

    def handle_put_version_1(self, paths, user):
        if not auth_provider.has_access(user, paths, "put"):
            self._drain_request_body()
            self.send_response(403)
            self.end_headers()
            return
        if paths[0] == "locations":
            location_id = int(paths[1])
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            updated_location = json.loads(post_data.decode())
            location_pool = data_provider.fetch_location_pool()
            if location_pool.get_location(location_id) is None:
                self.send_response(404)
                self.end_headers()
                return
            location_pool.update_location(location_id, updated_location)
            location_pool.save()
            self.send_response(200)
            self.end_headers()
        elif paths[0] == "items":
            item_id = int(paths[1])
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            updated_item = json.loads(post_data.decode())
            item_pool = data_provider.fetch_item_pool()
            if item_pool.get_item(item_id) is None:
                self.send_response(404)
                self.end_headers()
                return
            item_pool.update_item(item_id, updated_item)
            item_pool.save()
            self.send_response(200)
            self.end_headers()
        elif paths[0] == "item_lines":
            item_line_id = int(paths[1])
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            updated_item_line = json.loads(post_data.decode())
            item_line_pool = data_provider.fetch_item_line_pool()
            if item_line_pool.get_item_line(item_line_id) is None:
                self.send_response(404)
                self.end_headers()
                return
            item_line_pool.update_item_line(item_line_id, updated_item_line)
            item_line_pool.save()
            self.send_response(200)
            self.end_headers()
        elif paths[0] == "item_types":
            item_type_id = int(paths[1])
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            updated_item_type = json.loads(post_data.decode())
            item_type_pool = data_provider.fetch_item_type_pool()
            if item_type_pool.get_item_type(item_type_id) is None:
                self.send_response(404)
                self.end_headers()
                return
            item_type_pool.update_item_type(item_type_id, updated_item_type)
            item_type_pool.save()
            self.send_response(200)
            self.end_headers()
        elif paths[0] == "inventories":
            # Inventory rows are keyed on a composite (item_id, location_id); a
            # single surrogate id is not meaningful in the new schema.
            self.send_response(404)
            self.end_headers()
        elif paths[0] == "orders":
            parts = len(paths)
            match parts:
                case 2:
                    order_id = int(paths[1])
                    content_length = int(self.headers["Content-Length"])
                    post_data = self.rfile.read(content_length)
                    updated_order = json.loads(post_data.decode())
                    order_pool = data_provider.fetch_order_pool()
                    if order_pool.get_order(order_id) is None:
                        self.send_response(404)
                        self.end_headers()
                        return
                    order_pool.update_order(order_id, updated_order)
                    order_pool.save()
                    self.send_response(200)
                    self.end_headers()
                case 3:
                    if paths[2] == "items":
                        order_id = int(paths[1])
                        content_length = int(self.headers["Content-Length"])
                        post_data = self.rfile.read(content_length)
                        updated_items = json.loads(post_data.decode())
                        data_provider.fetch_order_pool().update_items_in_order(
                            order_id, updated_items
                        )
                        data_provider.fetch_order_pool().save()
                        self.send_response(200)
                        self.end_headers()
                    else:
                        self.send_response(404)
                        self.end_headers()
                case _:
                    self.send_response(404)
                    self.end_headers()
        elif paths[0] == "clients":
            client_id = int(paths[1])
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            updated_client = json.loads(post_data.decode())
            client_pool = data_provider.fetch_client_pool()
            if client_pool.get_client(client_id) is None:
                self.send_response(404)
                self.end_headers()
                return
            client_pool.update_client(client_id, updated_client)
            client_pool.save()
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def handle_delete_version_1(self, paths, user):
        if not auth_provider.has_access(user, paths, "delete"):
            self._drain_request_body()
            self.send_response(403)
            self.end_headers()
            return
        if paths[0] == "locations":
            location_id = int(paths[1])
            location_pool = data_provider.fetch_location_pool()
            if location_pool.get_location(location_id) is None:
                self.send_response(404)
                self.end_headers()
                return
            location_pool.remove_location(location_id)
            location_pool.save()
            self.send_response(200)
            self.end_headers()
        elif paths[0] == "items":
            item_id = int(paths[1])
            item_pool = data_provider.fetch_item_pool()
            if item_pool.get_item(item_id) is None:
                self.send_response(404)
                self.end_headers()
                return
            item_pool.remove_item(item_id)
            item_pool.save()
            self.send_response(200)
            self.end_headers()
        elif paths[0] == "item_lines":
            item_line_id = int(paths[1])
            item_line_pool = data_provider.fetch_item_line_pool()
            if item_line_pool.get_item_line(item_line_id) is None:
                self.send_response(404)
                self.end_headers()
                return
            item_line_pool.remove_item_line(item_line_id)
            item_line_pool.save()
            self.send_response(200)
            self.end_headers()
        elif paths[0] == "item_types":
            item_type_id = int(paths[1])
            item_type_pool = data_provider.fetch_item_type_pool()
            if item_type_pool.get_item_type(item_type_id) is None:
                self.send_response(404)
                self.end_headers()
                return
            item_type_pool.remove_item_type(item_type_id)
            item_type_pool.save()
            self.send_response(200)
            self.end_headers()
        elif paths[0] == "inventories":
            self.send_response(404)
            self.end_headers()
        elif paths[0] == "orders":
            order_id = int(paths[1])
            order_pool = data_provider.fetch_order_pool()
            if order_pool.get_order(order_id) is None:
                self.send_response(404)
                self.end_headers()
                return
            order_pool.remove_order(order_id)
            order_pool.save()
            self.send_response(200)
            self.end_headers()
        elif paths[0] == "clients":
            client_id = int(paths[1])
            client_pool = data_provider.fetch_client_pool()
            if client_pool.get_client(client_id) is None:
                self.send_response(404)
                self.end_headers()
                return
            client_pool.remove_client(client_id)
            client_pool.save()
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


# endregion

if __name__ == "__main__":
    PORT = 3000
    with socketserver.TCPServer(("", PORT), ApiRequestHandler) as httpd:
        notification_processor.start()
        print(f"Serving on port {PORT}...")
        httpd.serve_forever()
