from controllers.IResource import IResource
from providers import data_provider


class Items(IResource):
    sub_resource = "inventory"

    def get(self, resource_id=None):
        item_pool = data_provider.fetch_item_pool()
        if resource_id is None:
            return item_pool.get_items()
        return item_pool.get_item(resource_id)

    def get_sub_resource(self, resource_id):
        return data_provider.fetch_inventory_pool().get_inventories_for_item(
            resource_id
        )
    
    def get_sub_resource_totals(self, resource_id):
        return data_provider.fetch_inventory_pool().get_inventory_totals_for_item(
            resource_id
        )

    def post(self, data):
        item_pool = data_provider.fetch_item_pool()
        item_pool.add_item(data)
        item_pool.save()
        return data

    def put(self, resource_id, data):
        item_pool = data_provider.fetch_item_pool()
        if item_pool.get_item(resource_id) is None:
            return None
        item_pool.update_item(resource_id, data)
        item_pool.save()
        return data

    def delete(self, resource_id):
        item_pool = data_provider.fetch_item_pool()
        if item_pool.get_item(resource_id) is None:
            return None
        item_pool.remove_item(resource_id)
        item_pool.save()
        return True