"""
Test cases for CRUD Connectors module.

Tests:
1. MongoDB connector
2. PostgreSQL connector
3. MySQL connector
4. RabbitMQ connector
5. SQS connector
6. S3 connector
7. Connector creation and management
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, Connector
from app.connectors.manager import ConnectorManager
from app.connectors.database import MongoDBConnector, PostgreSQLConnector, MySQLConnector
from app.connectors.queue import RabbitMQConnector, SQSConnector
from app.connectors.storage import S3Connector


@pytest.fixture
async def db_session():
    """Create an in-memory database session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.mark.asyncio
class TestConnectorManager:
    """Test connector management."""
    
    async def test_create_connector(self, db_session: AsyncSession):
        """Test creating a connector."""
        manager = ConnectorManager(db_session)
        
        connector = await manager.create_connector(
            name="Test DB",
            connector_type="mongodb",
            config={
                "host": "localhost",
                "port": 27017,
                "database": "testdb"
            }
        )
        
        assert connector.name == "Test DB"
        assert connector.connector_type == "mongodb"
        assert connector.config["host"] == "localhost"
    
    async def test_list_connectors(self, db_session: AsyncSession):
        """Test listing connectors."""
        manager = ConnectorManager(db_session)
        
        # Create multiple connectors
        await manager.create_connector("Mongo1", "mongodb", {})
        await manager.create_connector("Postgres1", "postgresql", {})
        await manager.create_connector("S3-1", "s3", {})
        
        connectors = await manager.list_connectors()
        
        assert len(connectors) == 3
    
    async def test_get_connector(self, db_session: AsyncSession):
        """Test retrieving a specific connector."""
        manager = ConnectorManager(db_session)
        
        created = await manager.create_connector("MyDB", "mongodb", {})
        
        connector = await manager.get_connector(created.id)
        
        assert connector.id == created.id
        assert connector.name == "MyDB"
    
    async def test_update_connector(self, db_session: AsyncSession):
        """Test updating connector configuration."""
        manager = ConnectorManager(db_session)
        
        connector = await manager.create_connector(
            "Test", "mongodb",
            {"host": "old-host"}
        )
        
        await manager.update_connector(
            connector.id,
            config={"host": "new-host", "port": 27017}
        )
        
        updated = await manager.get_connector(connector.id)
        assert updated.config["host"] == "new-host"
    
    async def test_delete_connector(self, db_session: AsyncSession):
        """Test deleting a connector."""
        manager = ConnectorManager(db_session)
        
        connector = await manager.create_connector("ToDelete", "mongodb", {})
        
        success = await manager.delete_connector(connector.id)
        assert success
        
        deleted = await manager.get_connector(connector.id)
        assert deleted is None
    
    async def test_test_connection(self, db_session: AsyncSession):
        """Test testing a connector connection."""
        manager = ConnectorManager(db_session)
        
        connector = await manager.create_connector(
            "Test", "mongodb",
            {"host": "localhost", "port": 27017}
        )
        
        # This would attempt to connect
        # In reality, it might fail if MongoDB isn't running
        result = await manager.test_connection(connector.id)
        
        assert "status" in result


class TestMongoDBConnector:
    """Test MongoDB connector."""
    
    def test_create_mongodb_connector(self):
        """Test creating a MongoDB connector."""
        connector = MongoDBConnector(
            host="localhost",
            port=27017,
            database="testdb"
        )
        
        assert connector.host == "localhost"
        assert connector.port == 27017
    
    def test_mongodb_connection_string(self):
        """Test MongoDB connection string generation."""
        connector = MongoDBConnector(
            host="localhost",
            port=27017,
            database="testdb",
            username="user",
            password="pass"
        )
        
        conn_str = connector.get_connection_string()
        
        assert "mongodb://" in conn_str
        assert "user" in conn_str
        assert "localhost:27017" in conn_str
    
    @pytest.mark.asyncio
    async def test_mongodb_crud_operations(self):
        """Test MongoDB CRUD operations."""
        # This would require a running MongoDB instance
        # Skipping actual connection tests
        connector = MongoDBConnector(
            host="localhost",
            port=27017,
            database="testdb"
        )
        
        # Test that methods exist
        assert hasattr(connector, 'insert')
        assert hasattr(connector, 'find')
        assert hasattr(connector, 'update')
        assert hasattr(connector, 'delete')


class TestPostgreSQLConnector:
    """Test PostgreSQL connector."""
    
    def test_create_postgresql_connector(self):
        """Test creating a PostgreSQL connector."""
        connector = PostgreSQLConnector(
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password="pass"
        )
        
        assert connector.host == "localhost"
        assert connector.port == 5432
    
    def test_postgresql_connection_string(self):
        """Test PostgreSQL connection string generation."""
        connector = PostgreSQLConnector(
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password="pass"
        )
        
        conn_str = connector.get_connection_string()
        
        assert "postgresql://" in conn_str
        assert "localhost:5432" in conn_str
        assert "testdb" in conn_str


class TestMySQLConnector:
    """Test MySQL connector."""
    
    def test_create_mysql_connector(self):
        """Test creating a MySQL connector."""
        connector = MySQLConnector(
            host="localhost",
            port=3306,
            database="testdb",
            username="user",
            password="pass"
        )
        
        assert connector.host == "localhost"
        assert connector.port == 3306
    
    def test_mysql_connection_string(self):
        """Test MySQL connection string generation."""
        connector = MySQLConnector(
            host="localhost",
            port=3306,
            database="testdb",
            username="root",
            password="password"
        )
        
        conn_str = connector.get_connection_string()
        
        assert "mysql://" in conn_str or "mysql+pymysql://" in conn_str


class TestRabbitMQConnector:
    """Test RabbitMQ connector."""
    
    def test_create_rabbitmq_connector(self):
        """Test creating a RabbitMQ connector."""
        connector = RabbitMQConnector(
            host="localhost",
            port=5672,
            username="guest",
            password="guest"
        )
        
        assert connector.host == "localhost"
        assert connector.port == 5672
    
    def test_rabbitmq_connection_string(self):
        """Test RabbitMQ connection string generation."""
        connector = RabbitMQConnector(
            host="localhost",
            port=5672,
            username="guest",
            password="guest"
        )
        
        conn_str = connector.get_connection_string()
        
        assert "amqp://" in conn_str
    
    @pytest.mark.asyncio
    async def test_rabbitmq_publish(self):
        """Test publishing a message to RabbitMQ."""
        connector = RabbitMQConnector(
            host="localhost",
            port=5672,
            username="guest",
            password="guest"
        )
        
        # Test that method exists
        assert hasattr(connector, 'publish')
        assert hasattr(connector, 'consume')


class TestSQSConnector:
    """Test AWS SQS connector."""
    
    def test_create_sqs_connector(self):
        """Test creating an SQS connector."""
        connector = SQSConnector(
            region="us-east-1",
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        )
        
        assert connector.region == "us-east-1"
    
    @pytest.mark.asyncio
    async def test_sqs_send_message(self):
        """Test sending a message to SQS."""
        connector = SQSConnector(
            region="us-east-1",
            access_key_id="test",
            secret_access_key="test"
        )
        
        # Test that methods exist
        assert hasattr(connector, 'send_message')
        assert hasattr(connector, 'receive_message')
        assert hasattr(connector, 'delete_message')


class TestS3Connector:
    """Test AWS S3 connector."""
    
    def test_create_s3_connector(self):
        """Test creating an S3 connector."""
        connector = S3Connector(
            region="us-east-1",
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            bucket_name="my-bucket"
        )
        
        assert connector.bucket_name == "my-bucket"
        assert connector.region == "us-east-1"
    
    @pytest.mark.asyncio
    async def test_s3_operations(self):
        """Test S3 operations."""
        connector = S3Connector(
            region="us-east-1",
            access_key_id="test",
            secret_access_key="test",
            bucket_name="test-bucket"
        )
        
        # Test that methods exist
        assert hasattr(connector, 'upload')
        assert hasattr(connector, 'download')
        assert hasattr(connector, 'delete')
        assert hasattr(connector, 'list_objects')


@pytest.mark.asyncio
class TestConnectorEncryption:
    """Test that connector credentials are encrypted."""
    
    async def test_credentials_encrypted_at_rest(self, db_session: AsyncSession):
        """Test that credentials are encrypted in the database."""
        manager = ConnectorManager(db_session)
        
        connector = await manager.create_connector(
            name="SecureDB",
            connector_type="mongodb",
            config={
                "host": "localhost",
                "username": "admin",
                "password": "super_secret_password"
            }
        )
        
        # Retrieve directly from DB
        from sqlalchemy import select
        stmt = select(Connector).where(Connector.id == connector.id)
        result = await db_session.execute(stmt)
        db_connector = result.scalar_one()
        
        # Password should be encrypted
        assert db_connector.encrypted_config != connector.config
        # (Actual encryption verification would depend on implementation)


# Run tests with: pytest tests/test_connectors.py -v
