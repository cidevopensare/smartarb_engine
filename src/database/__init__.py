"""Database Manager"""

class DatabaseManager:
    def __init__(self, config):
        self.config = config
    
    async def initialize(self):
        return True
    
    async def start(self):
        pass
    
    async def test_connection(self):
        return True
    
    async def run_migrations(self):
        pass
