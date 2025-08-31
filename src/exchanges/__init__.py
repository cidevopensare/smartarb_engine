"""Exchange Manager"""

class ExchangeManager:
    def __init__(self, config):
        self.config = config
        self.exchanges = {}
    
    async def initialize(self):
        return True
    
    async def start(self):
        pass
    
    def get_connected_exchanges(self):
        return []
