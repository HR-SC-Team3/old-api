from pydantic import ValidationError

from validations.schema_validations import (   
    Warehouse,
    Location,
    Supplier,
    ItemGroup,
    Inventory,
    Order,
    Transfer,
    Shipment,
    Client,
    ItemType,
    Item,
    ItemLine,
    )

Schemas = { "item_groups": ItemGroup,
            "suppliers": Supplier,
            "transfers": Transfer,
            "inventories": Inventory,
            "shipments": Shipment,
            "warehouses": Warehouse,
            "orders": Order,
            "clients": Client,
            "item_types": ItemType,
            "locations": Location,
            "items": Item,
            "item_lines": ItemLine,
            }

class RequestValidator:
    @staticmethod
    def validate(resource, data, controllers, method="POST", resource_id=None):
        schema = Schemas.get(resource)
        if schema is None:
            return False, "Unknown resource"
        if not isinstance(data, dict):
            return False, "Request body must be a JSON object"

        valid, error = RequestValidator.validate_unexpected_fields(schema, data)
        if not valid:
            return False, error
        
        try:
            schema.model_validate(data)
        except ValidationError as error:
            return False, str(error)

        if method in ("POST", "PUT"):
            valid, error = RequestValidator.validate_duplicate_id(resource, data, controllers, resource_id)
            if not valid:
                return False, error   
        
        valid, error = RequestValidator.validate_foreign_key(resource, data, controllers)
        if not valid:
            return False, error
        
        valid, error = RequestValidator.validate_unique_fields(resource, data, controllers, resource_id)
        if not valid:
            return False, error
        return True, None
    
    @staticmethod
    def validate_unexpected_fields(schema, data):
        allowed_fields = schema.model_fields.keys()
        unexpected = set(data.keys()) - set(allowed_fields)
        if unexpected:
            return False, f"Unexpected fields: {', '.join(unexpected)}"
        return True, None
    
    @staticmethod
    def validate_duplicate_id(resource, data, controllers, resource_id=None):
        if resource == "transfers" and "id" not in data:
            return False, "Transfer id is required"
        if "id" not in data:
            return True, None
        controller = controllers[resource]
        if (controller.get(data["id"]) is not None and data["id"] != resource_id):
            return False, "Id already exists"
        return True, None
    
    @staticmethod
    def validate_foreign_key(resource, data, controllers):
        if resource == "items":
            if "item_line_id" in data:
                if controllers["item_lines"].get(data["item_line_id"]) is None:
                    return False, "Invalid item_line_id"
            if "item_group_id" in data:
                if controllers["item_groups"].get(data["item_group_id"]) is None:
                    return False, "Invalid item_group_id"
            if "item_type_id" in data:
                if controllers["item_types"].get(data["item_type_id"]) is None:
                    return False, "Invalid item_type_id"
            if "supplier_id" in data:
                if controllers["suppliers"].get(data["supplier_id"]) is None:
                    return False, "Invalid supplier_id"

        elif resource == "locations":
            if "warehouse_id" in data:
                if controllers["warehouses"].get(data["warehouse_id"]) is None:
                    return False, "Invalid warehouse_id"

        elif resource == "inventories":
            if "item_id" in data:
                if controllers["items"].get(data["item_id"]) is None:
                    return False, "Invalid item_id"
            if "location_id" in data:
                if controllers["locations"].get(data["location_id"]) is None:
                    return False, "Invalid location_id"

        elif resource == "transfers":
            if "from_location_id" in data:
                if controllers["locations"].get(data["from_location_id"]) is None:
                    return False, "Invalid from_location_id"
            if "to_location_id" in data:
                if controllers["locations"].get(data["to_location_id"]) is None:
                    return False, "Invalid to_location_id"
            if "items" in data:
                for item in data["items"]:
                    if controllers["items"].get(item.get("item_id")) is None:
                        return False, "Invalid item_id"

        elif resource == "shipments":
            if "order_id" in data:
                if controllers["orders"].get(data["order_id"]) is None:
                    return False, "Invalid order_id"

        elif resource == "orders":
            if "client_id" in data:
                if controllers["clients"].get(data["client_id"]) is None:
                    return False, "Invalid client_id"
            if "warehouse_id" in data:
                if controllers["warehouses"].get(data["warehouse_id"]) is None:
                    return False, "Invalid warehouse_id"
            if "ship_to_client_id" in data:
                if controllers["clients"].get(data["ship_to_client_id"]) is None:
                    return False, "Invalid ship_to_client_id"
            if "bill_to_client_id" in data:
                if controllers["clients"].get(data["bill_to_client_id"]) is None:
                    return False, "Invalid bill_to_client_id"
            if "items" in data:
                for item in data["items"]:
                    if controllers["items"].get(item.get("item_id")) is None:
                        return False, "Invalid item_id"
        return True, None

    @staticmethod
    def validate_unique_fields(resource, data, controllers, resource_id=None):
        if resource == "suppliers":
            if "code" not in data:
                return True, None
            records = controllers["suppliers"].get()
            for record in records:
                if record["id"] == resource_id:
                    continue
                if record["code"] == data["code"]:
                    return False, "Supplier code already exists"
                
        elif resource == "warehouses":
            if "code" not in data:
                return True, None
            records = controllers["warehouses"].get()
            for record in records:
                if record["id"] == resource_id:
                    continue
                if record["code"] == data["code"]:
                    return False, "Warehouse code already exists"
        return True, None