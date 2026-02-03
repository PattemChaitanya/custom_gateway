"""Queue connectors for message queues."""

from typing import Dict, Any, Optional
import redis.asyncio as redis
from app.logging_config import get_logger

logger = get_logger("queue_connector")


class QueueConnector:
    """Base class for queue connectors."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection = None
    
    async def connect(self):
        """Connect to queue."""
        raise NotImplementedError
    
    async def disconnect(self):
        """Disconnect from queue."""
        raise NotImplementedError
    
    async def publish(self, topic: str, message: Any):
        """Publish message to queue."""
        raise NotImplementedError
    
    async def subscribe(self, topic: str):
        """Subscribe to queue topic."""
        raise NotImplementedError
    
    async def health_check(self) -> bool:
        """Check queue connection."""
        raise NotImplementedError


class RedisQueueConnector(QueueConnector):
    """Redis queue connector."""
    
    async def connect(self):
        """Connect to Redis."""
        try:
            redis_url = self.config.get("url", "redis://localhost:6379/0")
            self.connection = await redis.from_url(redis_url, decode_responses=True)
            logger.info("Connected to Redis queue")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.connection:
            await self.connection.close()
            logger.info("Disconnected from Redis")
    
    async def publish(self, topic: str, message: str):
        """Publish message to Redis channel."""
        if not self.connection:
            raise RuntimeError("Not connected to Redis")
        
        await self.connection.publish(topic, message)
        logger.debug(f"Published message to {topic}")
    
    async def subscribe(self, topic: str):
        """Subscribe to Redis channel."""
        if not self.connection:
            raise RuntimeError("Not connected to Redis")
        
        pubsub = self.connection.pubsub()
        await pubsub.subscribe(topic)
        logger.info(f"Subscribed to {topic}")
        return pubsub
    
    async def push(self, queue: str, message: str):
        """Push message to Redis list (queue)."""
        if not self.connection:
            raise RuntimeError("Not connected to Redis")
        
        await self.connection.rpush(queue, message)
    
    async def pop(self, queue: str, timeout: int = 0):
        """Pop message from Redis list (queue)."""
        if not self.connection:
            raise RuntimeError("Not connected to Redis")
        
        result = await self.connection.blpop(queue, timeout=timeout)
        return result[1] if result else None
    
    async def health_check(self) -> bool:
        """Check Redis connection."""
        try:
            if not self.connection:
                return False
            await self.connection.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


class KafkaQueueConnector(QueueConnector):
    """Kafka queue connector (placeholder - requires aiokafka)."""
    
    async def connect(self):
        """Connect to Kafka."""
        logger.warning("Kafka connector not fully implemented")
        raise NotImplementedError("Kafka connector requires aiokafka package")
    
    async def disconnect(self):
        """Disconnect from Kafka."""
        pass
    
    async def publish(self, topic: str, message: Any):
        """Publish message to Kafka topic."""
        raise NotImplementedError
    
    async def subscribe(self, topic: str):
        """Subscribe to Kafka topic."""
        raise NotImplementedError
    
    async def health_check(self) -> bool:
        """Check Kafka connection."""
        return False


def create_queue_connector(queue_type: str, config: Dict[str, Any]) -> QueueConnector:
    """Factory function to create queue connector."""
    if queue_type == "redis":
        return RedisQueueConnector(config)
    elif queue_type == "kafka":
        return KafkaQueueConnector(config)
    else:
        raise ValueError(f"Unsupported queue type: {queue_type}")
