from controllers.IResource import IResource
from providers import data_provider
from processors import notification_processor


class Transfers(IResource):
    sub_resource = "items"

    def get(self, resource_id=None):
        pool = data_provider.fetch_transfer_pool()
        if resource_id is None:
            return pool.get_transfers()
        return pool.get_transfer(resource_id)

    def get_sub_resource(self, resource_id):
        return data_provider.fetch_transfer_pool().get_items_in_transfer(
            resource_id
        )

    def post(self, data):
        pool = data_provider.fetch_transfer_pool()
        pool.add_transfer(data)
        pool.save()
        notification_processor.push(f"Scheduled batch transfer {data['id']}")
        return data

    def put(self, resource_id, data):
        pool = data_provider.fetch_transfer_pool()
        if pool.get_transfer(resource_id) is None:
            return None
        pool.update_transfer(resource_id, data)
        pool.save()
        return data

    def delete(self, resource_id):
        pool = data_provider.fetch_transfer_pool()
        if pool.get_transfer(resource_id) is None:
            return None
        pool.remove_transfer(resource_id)
        pool.save()
        return True

    def commit(self, resource_id):
        transfer = data_provider.fetch_transfer_pool().get_transfer(resource_id)
        from_location_id = transfer["from_location_id"]
        to_location_id = transfer["to_location_id"]
        inventory_pool = data_provider.fetch_inventory_pool()
        for x in transfer["items"]:
            item_id = x["item_id"]
            amount = x["amount"]
            # decrease on-hand at the source location
            src = inventory_pool.get_inventory(item_id, from_location_id)
            if src is not None:
                src["quantity_on_hand"] -= amount
                inventory_pool.update_inventory(item_id, from_location_id, src)
            # increase (or create) on-hand at the destination location
            dst = inventory_pool.get_inventory(item_id, to_location_id)
            if dst is not None:
                dst["quantity_on_hand"] += amount
                inventory_pool.update_inventory(item_id, to_location_id, dst)
            else:
                inventory_pool.add_inventory(
                    {
                        "item_id": item_id,
                        "location_id": to_location_id,
                        "quantity_on_hand": amount,
                        "quantity_expected": 0,
                        "quantity_ordered": 0,
                        "quantity_allocated": 0,
                    }
                )
        transfer["transfer_status"] = "Processed"
        transfer.pop("items", None)
        data_provider.fetch_transfer_pool().update_transfer(resource_id, transfer)
        notification_processor.push(
            f"Processed batch transfer with id:{transfer['id']}"
        )
        data_provider.fetch_transfer_pool().save()
        data_provider.fetch_inventory_pool().save()
