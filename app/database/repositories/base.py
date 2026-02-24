"""
Base repository class with common database operations
"""
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional, Type, TypeVar, Generic
from uuid import uuid4

from ...logging import get_logger
from ..connection import Database

logger = get_logger(__name__)

T = TypeVar('T')


class BaseRepository(Generic[T], ABC):
    """Base repository with common database operations"""
    
    def __init__(self, database: Database, table_name: str):
        self.database = database
        self.table_name = table_name
        self.logger = logger.bind(table=table_name)
    
    @abstractmethod
    def _row_to_model(self, row: Dict[str, Any]) -> T:
        """Convert database row to model instance"""
        pass
    
    @abstractmethod
    def _model_to_dict(self, model: T) -> Dict[str, Any]:
        """Convert model instance to database dict"""
        pass
    
    def _serialize_json_field(self, value: Any) -> str:
        """Serialize a field to JSON string"""
        if value is None:
            return "{}"
        if isinstance(value, str):
            return value
        return json.dumps(value)
    
    def _deserialize_json_field(self, value: str) -> Any:
        """Deserialize a JSON string field"""
        if not value:
            return {}
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def _generate_id(self) -> str:
        """Generate a new UUID for entity"""
        return str(uuid4())
    
    def _get_current_timestamp(self) -> datetime:
        """Get current timestamp"""
        return datetime.utcnow()
    
    def create(self, model: T) -> T:
        """Create a new entity"""
        data = self._model_to_dict(model)
        
        # Ensure ID and timestamps are set
        if 'id' not in data or not data['id']:
            data['id'] = self._generate_id()
        
        if 'created_at' not in data:
            data['created_at'] = self._get_current_timestamp()
        
        if 'updated_at' not in data:
            data['updated_at'] = data['created_at']
        
        # Build INSERT query
        columns = list(data.keys())
        placeholders = [f":{col}" for col in columns]
        
        query = f"""
        INSERT INTO {self.table_name} ({', '.join(columns)})
        VALUES ({', '.join(placeholders)})
        """
        
        try:
            self.database.execute(query, data)
            self.logger.info("entity_created", entity_id=data['id'])
            
            # Return the created entity
            return self.get_by_id(data['id'])
        
        except Exception as e:
            self.logger.error("entity_create_failed", error=str(e), data=data)
            raise
    
    def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get entity by ID"""
        query = f"SELECT * FROM {self.table_name} WHERE id = :id"
        
        try:
            row = self.database.fetch_one(query, {"id": entity_id})
            if row:
                return self._row_to_model(dict(row))
            return None
        
        except Exception as e:
            self.logger.error("entity_get_failed", entity_id=entity_id, error=str(e))
            raise
    
    def update(self, entity_id: str, updates: Dict[str, Any]) -> Optional[T]:
        """Update entity by ID"""
        if not updates:
            return self.get_by_id(entity_id)
        
        # Add updated_at timestamp
        updates = updates.copy()
        updates['updated_at'] = self._get_current_timestamp()
        
        # Build UPDATE query
        set_clauses = [f"{col} = :{col}" for col in updates.keys()]
        query = f"""
        UPDATE {self.table_name} 
        SET {', '.join(set_clauses)}
        WHERE id = :id
        """
        
        updates['id'] = entity_id
        
        try:
            cursor = self.database.execute(query, updates)
            if cursor.rowcount > 0:
                self.logger.info("entity_updated", entity_id=entity_id, updated_fields=list(updates.keys()))
                return self.get_by_id(entity_id)
            else:
                self.logger.warning("entity_update_no_rows", entity_id=entity_id)
                return None
        
        except Exception as e:
            self.logger.error("entity_update_failed", entity_id=entity_id, error=str(e))
            raise
    
    def delete(self, entity_id: str) -> bool:
        """Delete entity by ID"""
        query = f"DELETE FROM {self.table_name} WHERE id = :id"
        
        try:
            cursor = self.database.execute(query, {"id": entity_id})
            success = cursor.rowcount > 0
            
            if success:
                self.logger.info("entity_deleted", entity_id=entity_id)
            else:
                self.logger.warning("entity_delete_not_found", entity_id=entity_id)
            
            return success
        
        except Exception as e:
            self.logger.error("entity_delete_failed", entity_id=entity_id, error=str(e))
            raise
    
    def list_all(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """List all entities with pagination"""
        query = f"SELECT * FROM {self.table_name} ORDER BY created_at DESC"
        
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        
        try:
            rows = self.database.fetch_all(query)
            return [self._row_to_model(dict(row)) for row in rows]
        
        except Exception as e:
            self.logger.error("entity_list_failed", error=str(e))
            raise
    
    def count(self, where_clause: Optional[str] = None, params: Optional[Dict[str, Any]] = None) -> int:
        """Count entities with optional filter"""
        query = f"SELECT COUNT(*) as count FROM {self.table_name}"
        
        if where_clause:
            query += f" WHERE {where_clause}"
        
        try:
            row = self.database.fetch_one(query, params or {})
            return row["count"] if row else 0
        
        except Exception as e:
            self.logger.error("entity_count_failed", error=str(e))
            raise
    
    def exists(self, entity_id: str) -> bool:
        """Check if entity exists"""
        query = f"SELECT 1 FROM {self.table_name} WHERE id = :id LIMIT 1"
        
        try:
            row = self.database.fetch_one(query, {"id": entity_id})
            return row is not None
        
        except Exception as e:
            self.logger.error("entity_exists_failed", entity_id=entity_id, error=str(e))
            raise
    
    def find_by(self, filters: Dict[str, Any], limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """Find entities by filters"""
        if not filters:
            return self.list_all(limit, offset)
        
        where_clauses = [f"{col} = :{col}" for col in filters.keys()]
        query = f"""
        SELECT * FROM {self.table_name} 
        WHERE {' AND '.join(where_clauses)}
        ORDER BY created_at DESC
        """
        
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        
        try:
            rows = self.database.fetch_all(query, filters)
            return [self._row_to_model(dict(row)) for row in rows]
        
        except Exception as e:
            self.logger.error("entity_find_failed", filters=filters, error=str(e))
            raise
    
    def find_one_by(self, filters: Dict[str, Any]) -> Optional[T]:
        """Find one entity by filters"""
        results = self.find_by(filters, limit=1)
        return results[0] if results else None
    
    def bulk_create(self, models: List[T]) -> int:
        """Create multiple entities in bulk"""
        if not models:
            return 0
        
        data_list = []
        for model in models:
            data = self._model_to_dict(model)
            
            # Ensure ID and timestamps
            if 'id' not in data or not data['id']:
                data['id'] = self._generate_id()
            
            timestamp = self._get_current_timestamp()
            if 'created_at' not in data:
                data['created_at'] = timestamp
            if 'updated_at' not in data:
                data['updated_at'] = timestamp
            
            data_list.append(data)
        
        # Build INSERT query
        if not data_list:
            return 0
        
        columns = list(data_list[0].keys())
        placeholders = [f":{col}" for col in columns]
        
        query = f"""
        INSERT INTO {self.table_name} ({', '.join(columns)})
        VALUES ({', '.join(placeholders)})
        """
        
        try:
            self.database.execute_many(query, data_list)
            self.logger.info("entities_bulk_created", count=len(data_list))
            return len(data_list)
        
        except Exception as e:
            self.logger.error("entities_bulk_create_failed", count=len(data_list), error=str(e))
            raise
    
    def bulk_update(self, updates_list: List[Dict[str, Any]]) -> int:
        """Update multiple entities in bulk"""
        if not updates_list:
            return 0
        
        updated_count = 0
        
        with self.database.transaction():
            for updates in updates_list:
                if 'id' not in updates:
                    continue
                
                entity_id = updates.pop('id')
                if self.update(entity_id, updates):
                    updated_count += 1
        
        self.logger.info("entities_bulk_updated", count=updated_count)
        return updated_count
    
    def execute_custom_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute custom query and return raw results"""
        try:
            rows = self.database.fetch_all(query, params or {})
            return [dict(row) for row in rows]
        
        except Exception as e:
            self.logger.error("custom_query_failed", query=query, error=str(e))
            raise