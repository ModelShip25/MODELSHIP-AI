"""
Supabase client wrapper for ModelShip backend.
Handles both real Supabase connections and mock implementations for development.
"""

import logging
from typing import Optional, Dict, Any, List, Union
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from supabase.client import AsyncClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class MockSupabaseClient(AsyncClient):
    """Mock Supabase client for development/testing when real credentials aren't available."""
    
    def __init__(self):
        # Initialize with dummy values to satisfy AsyncClient
        super().__init__(
            supabase_url="http://mock",
            supabase_key="mock",
            options=ClientOptions()
        )
        self.data = {
            "images": [],
            "annotations": [],
            "users": [],
            "jobs": [],
            "exports": []
        }
        logger.info("Using mock Supabase client for development")
    
    def table(self, table_name: str):
        return MockTable(table_name, self.data)
    
    @property
    def storage(self):
        return MockStorage()


class MockTable:
    """Mock table operations."""
    
    def __init__(self, table_name: str, data: Dict):
        self.table_name = table_name
        self.data = data
        self.query_filters = {}
        self.query_select = "*"
    
    def select(self, columns: str = "*"):
        self.query_select = columns
        return self
    
    def eq(self, column: str, value: Any):
        self.query_filters[column] = value
        return self
    
    def insert(self, data: Dict):
        # Generate UUID if not provided
        if "id" not in data:
            import uuid
            data["id"] = str(uuid.uuid4())
        
        self.data.setdefault(self.table_name, []).append(data)
        return MockExecuteResult(data)
    
    def update(self, data: Dict):
        # Find and update matching records
        table_data = self.data.get(self.table_name, [])
        for item in table_data:
            if all(item.get(k) == v for k, v in self.query_filters.items()):
                item.update(data)
        return MockExecuteResult(data)
    
    def delete(self):
        # Delete matching records
        table_data = self.data.get(self.table_name, [])
        self.data[self.table_name] = [
            item for item in table_data
            if not all(item.get(k) == v for k, v in self.query_filters.items())
        ]
        return MockExecuteResult({})
    
    def single(self):
        return self
    
    def execute(self):
        # Execute the query
        table_data = self.data.get(self.table_name, [])
        
        # Apply filters
        filtered_data = [
            item for item in table_data
            if all(item.get(k) == v for k, v in self.query_filters.items())
        ]
        
        return MockExecuteResult(filtered_data[0] if filtered_data else None)


class MockExecuteResult:
    """Mock execute result."""
    
    def __init__(self, data):
        self.data = data


class MockStorage:
    """Mock storage operations."""
    
    def list_buckets(self):
        return [{"name": "images"}, {"name": "previews"}]
    
    def create_bucket(self, name: str, public: bool = False):
        return {"name": name, "public": public}
    
    def from_(self, bucket_name: str):
        return MockBucket(bucket_name)


class MockBucket:
    """Mock bucket operations."""
    
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
    
    def upload(self, path: str, file, file_options: Dict[str, Any] = {}) -> Dict[str, str]:
        logger.info(f"Mock upload to {self.bucket_name}/{path}")
        return {"path": path}
    
    def get_public_url(self, path: str) -> str:
        return f"https://mock-storage.supabase.co/storage/v1/object/public/{self.bucket_name}/{path}"
    
    def delete(self, path: str) -> Dict[str, str]:
        logger.info(f"Mock delete from {self.bucket_name}/{path}")
        return {"path": path}


def get_supabase_client() -> AsyncClient:
    """Get Supabase client, using mock if real credentials aren't available."""
    try:
        # Check if we have real credentials
        if (settings.SUPABASE_URL and settings.SUPABASE_KEY and 
            not settings.SUPABASE_URL.startswith("your_") and 
            not settings.SUPABASE_KEY.startswith("your_")):
            
            # Use real Supabase client
            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            logger.info("Connected to real Supabase instance")
            return client
        else:
            # Use mock client for development
            logger.warning("Using mock Supabase client - set real credentials for production")
            return MockSupabaseClient()
            
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        logger.info("Falling back to mock client")
        return MockSupabaseClient()


# Global client instance
supabase_client = get_supabase_client() 