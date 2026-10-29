from controllers.IResource import IResource
from providers import data_provider


class Orders(IResource):
    sub_resource = "items"

    def get(self, resource_id=None):
        order_pool = data_provider.fetch_order_pool()

        if resource_id is None:
            return order_pool.get_orders()

        return order_pool.get_order(resource_id)

    def get_sub_resource(self, resource_id):
        return data_provider.fetch_order_pool().get_items_in_order(resource_id)

    def post(self, data):
        order_pool = data_provider.fetch_order_pool()
        order_pool.add_order(data)
        order_pool.save()
        return data

    def put(self, resource_id, data):
        order_pool = data_provider.fetch_order_pool()

        if order_pool.get_order(resource_id) is None:
            return None

        order_pool.update_order(resource_id, data)
        order_pool.save()
        return True

    def put_items(self, resource_id, data):
        order_pool = data_provider.fetch_order_pool()
        order_pool.update_items_in_order(resource_id, data)
        order_pool.save()

    def delete(self, resource_id):
        order_pool = data_provider.fetch_order_pool()

        if order_pool.get_order(resource_id) is None:
            return None

        order_pool.remove_order(resource_id)
        order_pool.save()
        return True
