from controllers.IResource import IResource
from providers import data_provider


class Inventory(IResource):
    def get(self, resource_id=None, location_id=None):
        inventory_pool = data_provider.fetch_inventory_pool()
        if resource_id is None:
            return inventory_pool.get_inventories()
        if location_id is None:
            return None
        return inventory_pool.get_inventory(resource_id, location_id)

    def post(self, data):
        inventory_pool = data_provider.fetch_inventory_pool()
        inventory_pool.add_inventory(data)
        inventory_pool.save()
        return data

    # keep this for when the API needs to use it in the future
    def put(self, resource_id, location_id, data):
        inventory_pool = data_provider.fetch_inventory_pool()
        if inventory_pool.get_inventory(resource_id, location_id) is None:
            return None
        inventory_pool.update_inventory(resource_id, location_id, data)
        inventory_pool.save()
        return data

    # keep this for when the API needs to use it in the future
    def delete(self, resource_id, location_id):
        inventory_pool = data_provider.fetch_inventory_pool()
        if inventory_pool.get_inventory(resource_id, location_id) is None:
            return None
        inventory_pool.remove_inventory(resource_id, location_id)
        inventory_pool.save()
        return True
