from controllers.IResource import IResource
from providers import data_provider


class Warehouses(IResource):
    def __init__(self):
        super().__init__()
        self.warehouses = data_provider.fetch_warehouse_pool().get_warehouses()

    def get(self, resource_id=None):
        if resource_id is None:
            return self.warehouses
        else:
            return data_provider.fetch_warehouse_pool().get_warehouse(resource_id)
