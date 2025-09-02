#!/usr/bin/env python3
"""
Start SmartArb Engine REST API
"""

import uvicorn
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

if __name__ == "__main__":
    uvicorn.run(
        "src.api.rest_api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
