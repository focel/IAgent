import redis
import json
import os
from typing import Optional, Any, Dict, List
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    """Cliente Redis simple y limpio"""
    
    def __init__(self):
        self.host = os.getenv('REDIS_HOST', 'localhost')
        self.port = int(os.getenv('REDIS_PORT', 6379))
        self.db = int(os.getenv('REDIS_DB', 0))
        self.password = os.getenv('REDIS_PASSWORD', None)
        
        self._client = None
    
    @property
    def client(self) -> redis.Redis:
        """Obtiene el cliente Redis (singleton)"""
        if self._client is None:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,
                socket_timeout=5
            )
        return self._client
    
    def ping(self) -> bool:
        """Verifica conexión con Redis"""
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            return False
    
    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Guarda valor en Redis"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            return self.client.setex(key, expire, value)
        except Exception as e:
            logger.error(f"Error setting {key}: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """Obtiene valor de Redis"""
        try:
            value = self.client.get(key)
            if value is None:
                return None
            
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            logger.error(f"Error getting {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Elimina clave de Redis"""
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Error deleting {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Verifica si existe la clave"""
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"Error checking {key}: {e}")
            return False

    def add_to_stream(self, stream_key: str, data: Dict[str, Any]) -> Optional[str]:
        """Agrega un mensaje a un stream de Redis"""
        try:
            # Convertir valores a string para Redis
            stream_data = {k: str(v) for k, v in data.items()}
            return self.client.xadd(stream_key, stream_data)
        except Exception as e:
            logger.error(f"Error adding to stream {stream_key}: {e}")
            return None

    def get_stream_messages(self, stream_key: str, count: int = 100) -> List[Dict]:
        """Obtiene mensajes de un stream de Redis"""
        try:
            messages = self.client.xrange(stream_key, count=count)
            result = []
            for msg_id, msg_data in messages:
                result.append({
                    'id': msg_id,
                    'data': msg_data
                })
            return result
        except Exception as e:
            logger.error(f"Error reading stream {stream_key}: {e}")
            return []

    def get_stream_content(self, stream_key: str) -> str:
        """Obtiene todo el contenido de un stream como texto formateado"""
        try:
            messages = self.get_stream_messages(stream_key, count=1000)
            content_lines = []
            for msg in messages:
                role = msg['data'].get('role', 'unknown')
                text = msg['data'].get('content', '')
                timestamp = msg['data'].get('timestamp', '')
                if timestamp:
                    content_lines.append(f"[{timestamp}] {role}: {text}")
                else:
                    content_lines.append(f"{role}: {text}")
            return "\n".join(content_lines)
        except Exception as e:
            logger.error(f"Error getting stream content {stream_key}: {e}")
            return ""

    def delete_stream(self, stream_key: str) -> bool:
        """Elimina un stream completo de Redis"""
        try:
            # Redis no tiene comando directo para eliminar stream, 
            # así que eliminamos todas las claves relacionadas
            self.client.delete(stream_key)
            return True
        except Exception as e:
            logger.error(f"Error deleting stream {stream_key}: {e}")
            return False

# Instancia global
redis_client = RedisClient()