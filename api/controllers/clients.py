# from controllers.resource import IResource
# from providers import data_provider


# class Clients(IResource):
#     sub_resource = "orders"

#     def __init__(self):
#         self.client_pool = data_provider.fetch_client_pool()
#         self.order_pool = data_provider.fetch_order_pool()

#     def get(self, resource_id=None):
#         if resource_id is None:
#             return self.client_pool.get_clients()

#         return self.client_pool.get_client(resource_id)

#     def get_sub_resource(self, resource_id):
#         return self.order_pool.get_orders_for_client(resource_id)

#     def post(self, data):
#         self.client_pool.add_client(data)
#         self.client_pool.save()

#     def put(self, resource_id, data):
#         if self.client_pool.get_client(resource_id) is None:
#             return None

#         self.client_pool.update_client(resource_id, data)
#         self.client_pool.save()
#         return True

#     def delete(self, resource_id):
#         if self.client_pool.get_client(resource_id) is None:
#             return None

#         self.client_pool.remove_client(resource_id)
#         self.client_pool.save()
#         return True
