from controllers.IResource import IResource
from providers import data_provider


class ItemLines(IResource):
    sub_resource = "items"

    def get(self, resource_id=None):
        item_line_pool = data_provider.fetch_item_line_pool()
        if resource_id is None:
            return item_line_pool.get_item_lines()
        return item_line_pool.get_item_line(resource_id)

    def get_sub_resource(self, resource_id):
        if data_provider.fetch_item_line_pool().get_item_line(resource_id) is None:
            return None
        return data_provider.fetch_item_pool().get_items_for_item_line(
            resource_id
        )

    def post(self, data):
        item_line_pool = data_provider.fetch_item_line_pool()
        item_line_pool.add_item_line(data)
        item_line_pool.save()
        return data

    def put(self, resource_id, data):
        item_line_pool = data_provider.fetch_item_line_pool()
        if item_line_pool.get_item_line(resource_id) is None:
            return None
        item_line_pool.update_item_line(resource_id, data)
        item_line_pool.save()
        return data

    def delete(self, resource_id):
        item_line_pool = data_provider.fetch_item_line_pool()
        if item_line_pool.get_item_line(resource_id) is None:
            return None
        item_line_pool.remove_item_line(resource_id)
        item_line_pool.save()
        return True
