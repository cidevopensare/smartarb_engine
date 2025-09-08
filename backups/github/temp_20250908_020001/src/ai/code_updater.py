"""Code Updater"""

class CodeUpdater:
    def __init__(self, config, database_manager):
        self.config = config
        self.database_manager = database_manager
    
    async def initialize(self):
        return True
