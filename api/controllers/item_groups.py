from controllers.IResource import IResource
from providers import data_provider


class ItemGroups(IResource):
    sub_resource = "items"

    def get(self, resource_id=None):
        pool = data_provider.fetch_item_group_pool()
        if resource_id is None:
            return pool.get_item_groups()
        return pool.get_item_group(resource_id)

    def get_sub_resource(self, resource_id):
        return data_provider.fetch_item_pool().get_items_for_item_group(
            resource_id
        )

    def post(self, data):
        pool = data_provider.fetch_item_group_pool()
        pool.add_item_group(data)
        pool.save()
        return data

    def put(self, resource_id, data):
        pool = data_provider.fetch_item_group_pool()
        if pool.get_item_group(resource_id) is None:
            return None
        pool.update_item_group(resource_id, data)
        pool.save()
        return data

    def delete(self, resource_id):
        pool = data_provider.fetch_item_group_pool()
        if pool.get_item_group(resource_id) is None:
            return None
        pool.remove_item_group(resource_id)
        pool.save()
        return True
