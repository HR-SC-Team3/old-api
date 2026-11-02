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
from controllers.orders import Orders
from controllers.clients import Clients
from controllers.item_types import ItemTypes
from controllers.locations import Locations
from controllers.items import Items
from controllers.item_lines import Item_lines

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
            "inventories": Inventory(),
            "shipments": Shipment(),
            "warehouses": Warehouses(),
            "orders": Orders(),
            "clients": Clients(),
            "item_types": ItemTypes(),
            "locations": Locations(),
            "items": Items(),
            "item_lines": Item_lines(),
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
                        case "warehouses" | "suppliers" | "item_groups" | "transfers" | "orders" | "clients" | "item_types" | "locations" | "items" | "item_lines" :
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
                                case 4:
                                    if paths[5] == "inventory" and paths[6] == "totals":
                                        self.send_json_response(
                                            200, controller.get_sub_resource_totals(int(paths[4]))
                                        )
                                case _:
                                    self.send_response(404)
                                    self.end_headers()
                        case "inventories":
                            if self._deny_without_access(user, paths[3:], "get"):
                                return
                            controller = self.controllers["inventories"]
                            match len(paths) - 3:
                                case 1:
                                    self.send_json_response(200, controller.get())
                                case _:
                                    self.send_response(404)
                                    self.end_headers()
                        case "shipments":
                            if self._deny_without_access(user, paths[3:], "get"):
                                return
                            controller = self.controllers["shipments"]
                            match len(paths) - 3:
                                case 1:
                                    self.send_json_response(200, controller.get())
                                case 2:
                                    shipment = controller.get(int(paths[4]))
                                    if shipment is None:
                                        self.send_response(404)
                                        self.end_headers()
                                    else:
                                        self.send_json_response(200, shipment)
                                case 3 if paths[5] == "orders":
                                    orders = controller.get_orders(int(paths[4]))
                                    self.send_json_response(200, orders)
                                case 3 if paths[5] == "items":
                                    items = controller.get_items(int(paths[4]))
                                    self.send_json_response(200, items)
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

                        case "orders":
                            if self._deny_without_access(user, paths[3:], "put"):
                                return

                            controller = self.controllers["orders"]

                            match len(paths) - 3:
                                case 2:
                                    order_id = int(paths[4])
                                    updated_order = self._read_json_body()

                                    if controller.put(order_id, updated_order) is None:
                                        self.send_response(404)
                                    else:
                                        self.send_response(200)

                                    self.end_headers()

                                case 3 if paths[5] == "items":
                                    order_id = int(paths[4])
                                    updated_items = self._read_json_body()
                                    controller.put_items(order_id, updated_items)
                                    self.send_response(200)
                                    self.end_headers()

                                case _:
                                    self.send_response(404)
                                    self.end_headers()
                        case "warehouses" | "suppliers" | "item_groups" | "clients" | "item_types" | "locations" | "items" | "item_lines":
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
                            self.send_response(404)
                            self.end_headers()
                        case "shipments":
                            if self._deny_without_access(user, paths[3:], "put"):
                                return
                            controller = self.controllers["shipments"]
                            match len(paths) - 3:
                                case 2:
                                    shipment_id = int(paths[4])
                                    update_shipment = self._read_json_body()
                                    if controller.put(shipment_id, update_shipment) is None:
                                        self.send_response(404)
                                    else:
                                        self.send_response(200)
                                    self.end_headers()
                                case 3 if (paths[5]) == "orders":
                                    shipment_id = int(paths[4])
                                    updated_orders = self._read_json_body()
                                    if controller.put_orders(shipment_id, updated_orders) is None:
                                        self.send_response(404)
                                    else:
                                        self.send_response(200)
                                    self.end_headers()
                                case 3 if (paths[5]) =="items":
                                    shipment_id = int(paths[4])
                                    updated_items = self._read_json_body()
                                    if controller.put_items(shipment_id, updated_items) is None:
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
                        case "warehouses" | "suppliers" | "item_groups" | "transfers" | "orders" | "clients" | "item_types" | "locations" | "items" | "item_lines":
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
                            controller = self.controllers["inventories"]
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
                            controller.post(new_inventory)
                            self.send_response(201)
                            self.end_headers()
                        case "shipments":
                            if self._deny_without_access(user, paths[3:], "post"):
                                return
                            controller = self.controllers["shipments"]
                            media_type = (self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower())
                            if media_type != "application/json":
                                self._drain_request_body()
                                self.send_response(415)
                                self.end_headers()
                                return
                            new_shipment = self._read_json_body()
                            controller.post(new_shipment)
                            self.send_response(201)
                            self.end_headers()
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
                        case "warehouses" | "suppliers" | "item_groups" | "transfers" | "orders" | "clients" | "item_types" | "locations" | "items" | "item_lines":
                            if self._deny_without_access(user, paths[3:], "delete"):
                                return
                            if self.controllers[paths[3]].delete(int(paths[4])) is None:
                                self.send_response(404)
                            else:
                                self.send_response(200)
                            self.end_headers()
                        case "inventories":
                            if self._deny_without_access(user, paths[3:], "delete"):
                                return
                            self.send_response(404)
                            self.end_headers()
                        case "shipments":
                            if self._deny_without_access(user, paths[3:], "delete"):
                                return
                            controller = self.controllers["shipments"]
                            shipment_id = int(paths[4])
                            if controller.delete(shipment_id) is None:
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
        else:
            self.send_response(404)
            self.end_headers()

    def handle_put_version_1(self, paths, user):
        if not auth_provider.has_access(user, paths, "put"):
            self._drain_request_body()
            self.send_response(403)
            self.end_headers()
            return
        else:
            self.send_response(404)
            self.end_headers()

    def handle_delete_version_1(self, paths, user):
        if not auth_provider.has_access(user, paths, "delete"):
            self._drain_request_body()
            self.send_response(403)
            self.end_headers()
            return
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
