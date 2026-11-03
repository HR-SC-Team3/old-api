from controllers.IResource import IResource
from providers import data_provider


class Suppliers(IResource):
    sub_resource = "items"

    def get(self, resource_id=None):
        pool = data_provider.fetch_supplier_pool()
        if resource_id is None:
            return pool.get_suppliers()
        return pool.get_supplier(resource_id)

    def get_sub_resource(self, resource_id):
        return data_provider.fetch_item_pool().get_items_for_supplier(resource_id)

    def post(self, data):
        pool = data_provider.fetch_supplier_pool()
        pool.add_supplier(data)
        pool.save()
        return data

    def put(self, resource_id, data):
        pool = data_provider.fetch_supplier_pool()
        if pool.get_supplier(resource_id) is None:
            return None
        pool.update_supplier(resource_id, data)
        pool.save()
        return data

    def delete(self, resource_id):
        pool = data_provider.fetch_supplier_pool()
        if pool.get_supplier(resource_id) is None:
            return None
        pool.remove_supplier(resource_id)
        pool.save()
        return True
