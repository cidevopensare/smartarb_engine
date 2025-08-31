"""Monitoring Service"""

class MonitoringService:
    def __init__(self, config):
        self.config = config
    
    async def initialize(self):
        return True
    
    async def start(self):
        pass
