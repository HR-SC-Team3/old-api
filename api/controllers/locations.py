from controllers.IResource import IResource
from providers import data_provider

class Locations(IResource):
    def get(self, location_id = None):
        location_pool = data_provider.fetch_location_pool()
        if location_id is None:
            return location_pool.get_locations()    
        return location_pool.get_location(location_id)
    
    def post(self, data):
        location_pool = data_provider.fetch_location_pool()
        location_pool.add_location(data)
        location_pool.save()
        return data
    
    def put(self, location_id, data):
        location_pool = data_provider.fetch_location_pool()
        if location_pool.get_location(location_id) is None:
            return None
        location_pool.update_location(location_id, data)
        location_pool.save()
        return data
    
    def delete(self, location_id):
        location_pool = data_provider.fetch_location_pool()
        if location_pool.get_location(location_id) is None:
            return None
        location_pool.remove_location(location_id)
        location_pool.save()
        return True
    