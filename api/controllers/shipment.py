from controllers.IResource import IResource
from providers import data_provider

class Shipment(IResource):
    def get(self, shipment_id = None):
        shipment_pool = data_provider.fetch_shipment_pool()
        if shipment_id is None:
            return shipment_pool.get_shipments()
        return shipment_pool.get_shipment(shipment_id)

    def get_orders(self, shipment_id):
        shipment_pool = data_provider.fetch_shipment_pool()
        return shipment_pool.get_order_ids_in_shipment(shipment_id)
    
    def get_items(self, shipment_id):
        shipment_pool = data_provider.fetch_shipment_pool()
        return shipment_pool.get_items_in_shipment(shipment_id)

    def post(self, data):
        shipment_pool = data_provider.fetch_shipment_pool()
        shipment_pool.add_shipment(data)
        shipment_pool.save()


    def put(self, shipment_id, data):
        shipment_pool = data_provider.fetch_shipment_pool()
        if shipment_pool.get_shipment(shipment_id) is None:
            return None
        shipment_pool.update_shipment(shipment_id, data)
        shipment_pool.save()
        return True

    def put_orders(self, shipment_id, order_ids):
        shipment_pool = data_provider.fetch_shipment_pool()
        shipment_pool.update_orders_in_shipment(shipment_id, order_ids)
        shipment_pool.save()
        return True
    
    def put_items(self, shipment_id, items):
        shipment_pool = data_provider.fetch_shipment_pool()
        shipment_pool.update_items_in_shipment(shipment_id, items)
        shipment_pool.save()
        return True
    
    def delete(self, shipment_id):
        shipment_pool = data_provider.fetch_shipment_pool()
        if shipment_pool.get_shipment(shipment_id) is None:
            return None
        shipment_pool.remove_shipment(shipment_id)
        shipment_pool.save()
        return True
