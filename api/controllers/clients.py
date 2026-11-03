from controllers.IResource import IResource
from providers import data_provider


class Clients(IResource):
    sub_resource = "orders"

    def get(self, resource_id=None):
        client_pool = data_provider.fetch_client_pool()

        if resource_id is None:
            return client_pool.get_clients()

        return client_pool.get_client(resource_id)

    def get_sub_resource(self, resource_id):
        return data_provider.fetch_order_pool().get_orders_for_client(resource_id)

    def post(self, data):
        client_pool = data_provider.fetch_client_pool()
        client_pool.add_client(data)
        client_pool.save()
        return data

    def put(self, resource_id, data):
        client_pool = data_provider.fetch_client_pool()

        if client_pool.get_client(resource_id) is None:
            return None

        client_pool.update_client(resource_id, data)
        client_pool.save()
        return True

    def delete(self, resource_id):
        client_pool = data_provider.fetch_client_pool()

        if client_pool.get_client(resource_id) is None:
            return None

        client_pool.remove_client(resource_id)
        client_pool.save()
        return True
