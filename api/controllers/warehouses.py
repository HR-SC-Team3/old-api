from controllers.IResource import IResource
from providers import data_provider


class Warehouses(IResource):
    sub_resource = "locations"

    def get(self, resource_id=None):
        warehouse_pool = data_provider.fetch_warehouse_pool()
        if resource_id is None:
            return warehouse_pool.get_warehouses()
        return warehouse_pool.get_warehouse(resource_id)

    def get_sub_resource(self, resource_id):
        return data_provider.fetch_location_pool().get_locations_in_warehouse(
            resource_id
        )

    def post(self, data):
        warehouse_pool = data_provider.fetch_warehouse_pool()
        warehouse_pool.add_warehouse(data)
        warehouse_pool.save()
        return data

    def put(self, resource_id, data):
        warehouse_pool = data_provider.fetch_warehouse_pool()
        if warehouse_pool.get_warehouse(resource_id) is None:
            return None
        warehouse_pool.update_warehouse(resource_id, data)
        warehouse_pool.save()
        return data

    def delete(self, resource_id):
        warehouse_pool = data_provider.fetch_warehouse_pool()
        if warehouse_pool.get_warehouse(resource_id) is None:
            return None
        warehouse_pool.remove_warehouse(resource_id)
        warehouse_pool.save()
        return True
