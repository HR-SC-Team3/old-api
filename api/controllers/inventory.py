from controllers.IResource import IResource
from providers import data_provider


class Inventory(IResource):
    def get(self, resource_id = None, location_id = None):
        inventory_pool = data_provider.fetch_inventory_pool()
        if resource_id is None:
            return inventory_pool.get_inventories()
        if location_id is None:
            return inventory_pool.get_inventory(resource_id, location_id)
        return inventory_pool.get_inventories_for_item(resource_id, location_id)

    def get_totals(self, resource_id):
        inventory_pool = data_provider.fetch_inventory_pool()
        return inventory_pool.get_inventory_totals_for_item(resource_id)
    
    def post(self, data):
        Inventory_pool = data_provider.fetch_inventory_pool()
        Inventory_pool.add_inventory(data)
        Inventory_pool.save()
        return data


    def put(self, resource_id, location_id, data):
        Inventory_pool = data_provider.fetch_inventory_pool()
        if Inventory_pool.get_inventory(resource_id, location_id) is None:
            return None
        Inventory_pool.update_inventory(resource_id, location_id, data)
        Inventory_pool.save()
        return data

    def delete(self, resource_id, location_id):
        Inventory_pool = data_provider.fetch_inventory_pool()
        if Inventory_pool.get_inventory(resource_id, location_id) is None:
            return None
        Inventory_pool.remove_inventory(resource_id, location_id)
        Inventory_pool.save()
        return True
