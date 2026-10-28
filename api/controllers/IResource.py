class IResource:
    def __init__(self):
        pass

    def get(self, resource_id=None):
        raise NotImplementedError("Subclasses should implement this method.")

    def post(self, data):
        raise NotImplementedError("Subclasses should implement this method.")

    def put(self, resource_id, data):
        raise NotImplementedError("Subclasses should implement this method.")

    def delete(self, resource_id):
        raise NotImplementedError("Subclasses should implement this method.")
