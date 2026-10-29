
from controllers.IResource import IResource
from providers import data_provider


class ItemTypes(IResource):
    sub_resource = "items"

    def get(self, resource_id=None):
        item_type_pool = data_provider.fetch_item_type_pool()

        if resource_id is None:
            return item_type_pool.get_item_types()

        return item_type_pool.get_item_type(resource_id)

    def get_sub_resource(self, resource_id):
        return data_provider.fetch_item_pool().get_items_for_item_type(
            resource_id
        )
        
    def get(self, resource_id=None):
        item_type_pool = data_provider.fetch_item_type_pool()

        if resource_id is None:
            return item_type_pool.get_item_types()

        return item_type_pool.get_item_type(resource_id)

    def post(self, data):
        item_type_pool = data_provider.fetch_item_type_pool()
        item_type_pool.add_item_type(data)
        item_type_pool.save()
        return data

    def put(self, resource_id, data):
        item_type_pool = data_provider.fetch_item_type_pool()

        if item_type_pool.get_item_type(resource_id) is None:
            return None

        item_type_pool.update_item_type(resource_id, data)
        item_type_pool.save()
        return True

    def delete(self, resource_id):
        item_type_pool = data_provider.fetch_item_type_pool()

        if item_type_pool.get_item_type(resource_id) is None:
            return None

        item_type_pool.remove_item_type(resource_id)
        item_type_pool.save()
        return True
