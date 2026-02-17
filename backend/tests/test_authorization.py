"""
Test cases for Authorization (RBAC/ABAC) module.

Tests:
1. Role-based access control (RBAC)
2. Attribute-based access control (ABAC)
3. Permission checking
4. Role assignment
5. Policy evaluation
6. Resource access control
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, User, Role, Permission
from app.authorization.rbac import RBACManager
from app.authorization.abac import ABACManager, Policy
from app.authorization.decorators import require_permission, require_role


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
class TestRBAC:
    """Test Role-Based Access Control."""
    
    async def test_create_role(self, db_session: AsyncSession):
        """Test creating a role."""
        rbac = RBACManager(db_session)
        
        role = await rbac.create_role(
            name="admin",
            description="Administrator role"
        )
        
        assert role.name == "admin"
        assert role.description == "Administrator role"
    
    async def test_create_permission(self, db_session: AsyncSession):
        """Test creating a permission."""
        rbac = RBACManager(db_session)
        
        permission = await rbac.create_permission(
            name="api:read",
            description="Read APIs"
        )
        
        assert permission.name == "api:read"
    
    async def test_assign_permission_to_role(self, db_session: AsyncSession):
        """Test assigning permissions to a role."""
        rbac = RBACManager(db_session)
        
        role = await rbac.create_role("editor", "Editor role")
        perm1 = await rbac.create_permission("api:read", "Read APIs")
        perm2 = await rbac.create_permission("api:write", "Write APIs")
        
        await rbac.assign_permission_to_role(role.id, perm1.id)
        await rbac.assign_permission_to_role(role.id, perm2.id)
        
        permissions = await rbac.get_role_permissions(role.id)
        
        assert len(permissions) == 2
        assert any(p.name == "api:read" for p in permissions)
        assert any(p.name == "api:write" for p in permissions)
    
    async def test_assign_role_to_user(self, db_session: AsyncSession):
        """Test assigning a role to a user."""
        # First create a user
        from app.db.models import User
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=pwd_context.hash("password123")
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create role
        rbac = RBACManager(db_session)
        role = await rbac.create_role("viewer", "Viewer role")
        
        # Assign role to user
        await rbac.assign_role_to_user(user.id, role.id)
        
        # Check user roles
        user_roles = await rbac.get_user_roles(user.id)
        
        assert len(user_roles) == 1
        assert user_roles[0].name == "viewer"
    
    async def test_check_permission(self, db_session: AsyncSession):
        """Test checking if user has permission."""
        from app.db.models import User
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Create user
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=pwd_context.hash("password123")
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create role and permission
        rbac = RBACManager(db_session)
        role = await rbac.create_role("admin", "Admin")
        perm = await rbac.create_permission("api:delete", "Delete APIs")
        
        # Assign permission to role, role to user
        await rbac.assign_permission_to_role(role.id, perm.id)
        await rbac.assign_role_to_user(user.id, role.id)
        
        # Check permission
        has_permission = await rbac.user_has_permission(user.id, "api:delete")
        
        assert has_permission is True
    
    async def test_user_without_permission(self, db_session: AsyncSession):
        """Test that user without permission is denied."""
        from app.db.models import User
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=pwd_context.hash("password123")
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        rbac = RBACManager(db_session)
        
        # Check permission user doesn't have
        has_permission = await rbac.user_has_permission(user.id, "api:delete")
        
        assert has_permission is False


@pytest.mark.asyncio
class TestABAC:
    """Test Attribute-Based Access Control."""
    
    async def test_create_policy(self, db_session: AsyncSession):
        """Test creating an ABAC policy."""
        abac = ABACManager(db_session)
        
        policy = await abac.create_policy(
            name="ownership_policy",
            resource_type="api",
            rules={
                "condition": "user.id == resource.owner_id"
            }
        )
        
        assert policy.name == "ownership_policy"
        assert policy.resource_type == "api"
    
    async def test_evaluate_simple_policy(self, db_session: AsyncSession):
        """Test evaluating a simple policy."""
        abac = ABACManager(db_session)
        
        # Create ownership policy
        policy = Policy(
            name="ownership",
            rules={
                "condition": "user_id == resource_owner_id"
            }
        )
        
        # User owns the resource
        context = {
            "user_id": 123,
            "resource_owner_id": 123
        }
        
        result = policy.evaluate(context)
        assert result is True
        
        # User doesn't own the resource
        context = {
            "user_id": 123,
            "resource_owner_id": 456
        }
        
        result = policy.evaluate(context)
        assert result is False
    
    async def test_evaluate_time_based_policy(self, db_session: AsyncSession):
        """Test evaluating a time-based policy."""
        from datetime import datetime, timezone
        
        policy = Policy(
            name="business_hours",
            rules={
                "condition": "9 <= hour < 17"
            }
        )
        
        # During business hours
        context = {"hour": 10}
        assert policy.evaluate(context) is True
        
        # Outside business hours
        context = {"hour": 20}
        assert policy.evaluate(context) is False
    
    async def test_evaluate_role_based_abac_policy(self, db_session: AsyncSession):
        """Test evaluating a policy with role checks."""
        policy = Policy(
            name="admin_or_owner",
            rules={
                "condition": "user_role == 'admin' or user_id == resource_owner_id"
            }
        )
        
        # Admin user
        context = {
            "user_role": "admin",
            "user_id": 1,
            "resource_owner_id": 999
        }
        assert policy.evaluate(context) is True
        
        # Owner user
        context = {
            "user_role": "user",
            "user_id": 123,
            "resource_owner_id": 123
        }
        assert policy.evaluate(context) is True
        
        # Neither admin nor owner
        context = {
            "user_role": "user",
            "user_id": 123,
            "resource_owner_id": 456
        }
        assert policy.evaluate(context) is False
    
    async def test_complex_policy_evaluation(self, db_session: AsyncSession):
        """Test evaluating complex policies with multiple conditions."""
        policy = Policy(
            name="complex",
            rules={
                "conditions": [
                    "user_role in ['admin', 'moderator']",
                    "resource_status == 'active'",
                    "user_verified == True"
                ],
                "operator": "AND"
            }
        )
        
        # All conditions met
        context = {
            "user_role": "admin",
            "resource_status": "active",
            "user_verified": True
        }
        assert policy.evaluate(context) is True
        
        # One condition fails
        context = {
            "user_role": "admin",
            "resource_status": "inactive",
            "user_verified": True
        }
        assert policy.evaluate(context) is False


class TestAuthorizationDecorators:
    """Test authorization decorators."""
    
    @pytest.mark.asyncio
    async def test_require_permission_decorator(self):
        """Test @require_permission decorator."""
        
        @require_permission("api:read")
        async def read_api(user_id: int):
            return "API data"
        
        # This would require setting up a mock user context
        # For now, we just test that the decorator exists
        assert hasattr(read_api, '__wrapped__')
    
    @pytest.mark.asyncio
    async def test_require_role_decorator(self):
        """Test @require_role decorator."""
        
        @require_role("admin")
        async def admin_action(user_id: int):
            return "Admin action completed"
        
        assert hasattr(admin_action, '__wrapped__')


@pytest.mark.asyncio
class TestResourceAccessControl:
    """Test resource-level access control."""
    
    async def test_api_ownership_check(self, db_session: AsyncSession):
        """Test that users can only access their own APIs."""
        from app.db.models import User, API
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Create two users
        user1 = User(
            username="user1",
            email="user1@example.com",
            hashed_password=pwd_context.hash("password")
        )
        user2 = User(
            username="user2",
            email="user2@example.com",
            hashed_password=pwd_context.hash("password")
        )
        
        db_session.add_all([user1, user2])
        await db_session.commit()
        await db_session.refresh(user1)
        await db_session.refresh(user2)
        
        # Create API owned by user1
        api = API(
            name="Test API",
            description="Test",
            base_url="http://test.com",
            type="REST",
            user_id=user1.id
        )
        db_session.add(api)
        await db_session.commit()
        await db_session.refresh(api)
        
        # Check ownership
        abac = ABACManager(db_session)
        
        # User1 can access (owner)
        context = {
            "user_id": user1.id,
            "resource_owner_id": api.user_id
        }
        policy = Policy(name="ownership", rules={"condition": "user_id == resource_owner_id"})
        assert policy.evaluate(context) is True
        
        # User2 cannot access (not owner)
        context = {
            "user_id": user2.id,
            "resource_owner_id": api.user_id
        }
        assert policy.evaluate(context) is False


# Run tests with: pytest tests/test_authorization.py -v
