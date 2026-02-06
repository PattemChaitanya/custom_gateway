# Protecting API Endpoints with RBAC

This guide shows how to protect your API endpoints using the RBAC system.

## Method 1: Using Decorators (Recommended)

### Require Specific Permission

```python
from fastapi import APIRouter, Depends
from app.authorizers.rbac import require_permission

router = APIRouter()

@router.post("/apis")
async def create_api(
    api_data: APICreate,
    user = Depends(require_permission("api:create"))
):
    """Only users with 'api:create' permission can create APIs."""
    # Your implementation
    pass

@router.delete("/apis/{api_id}")
async def delete_api(
    api_id: int,
    user = Depends(require_permission("api:delete"))
):
    """Only users with 'api:delete' permission can delete APIs."""
    # Your implementation
    pass
```

### Require Specific Role

```python
from app.authorizers.rbac import require_role

@router.post("/users")
async def create_user(
    user_data: UserCreate,
    user = Depends(require_role("admin"))
):
    """Only users with 'admin' role can create users."""
    # Your implementation
    pass
```

### Multiple Permission Checks

```python
from fastapi import Depends, HTTPException, status

@router.put("/apis/{api_id}")
async def update_api(
    api_id: int,
    api_data: APIUpdate,
    user = Depends(require_permission("api:update")),
    db: AsyncSession = Depends(get_db)
):
    """Requires api:update permission."""
    
    # Optional: Additional ownership check
    api = await get_api(db, api_id)
    if api.owner_id != user.id and not user.is_superuser:
        # User doesn't own this API and isn't superuser
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update your own APIs"
        )
    
    # Your implementation
    pass
```

## Method 2: Manual Permission Check

For more complex scenarios, check permissions manually:

```python
from app.authorizers.rbac import RBACManager

@router.post("/apis/{api_id}/clone")
async def clone_api(
    api_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clone an API (requires both read and create permissions)."""
    
    manager = RBACManager(db)
    
    # Check multiple permissions
    can_read = await manager.user_has_permission(current_user.id, "api:read")
    can_create = await manager.user_has_permission(current_user.id, "api:create")
    
    if not (can_read and can_create):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires both api:read and api:create permissions"
        )
    
    # Your implementation
    pass
```

## Method 3: Conditional Permissions (ABAC)

Use the Policy Engine for attribute-based access control:

```python
from app.authorizers.policies import PolicyEngine, ResourcePermission

@router.put("/apis/{api_id}")
async def update_api(
    api_id: int,
    api_data: APIUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update API with conditional access."""
    
    # Get the API
    api = await get_api(db, api_id)
    
    # Create resource permission object
    resource = ResourcePermission(
        resource_type="api",
        resource_id=str(api_id),
        owner_id=api.owner_id,
        visibility=api.config.get("visibility", "private")
    )
    
    # Evaluate policy
    engine = PolicyEngine()
    user_dict = {
        "id": current_user.id,
        "roles": current_user.roles.split(",") if current_user.roles else [],
        "is_superuser": current_user.is_superuser
    }
    
    allowed = engine.evaluate(user_dict, resource, "update")
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this API"
        )
    
    # Your implementation
    pass
```

## Complete Example: Protected CRUD Endpoints

```python
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.connector import get_db
from app.db.models import User, API
from app.api.auth.auth_dependency import get_current_user
from app.authorizers.rbac import require_permission

router = APIRouter(prefix="/apis", tags=["APIs"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_api(
    api_data: APICreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("api:create"))
):
    """Create a new API. Requires api:create permission."""
    
    api = API(
        name=api_data.name,
        version=api_data.version,
        description=api_data.description,
        owner_id=user.id,  # Set current user as owner
        config=api_data.config
    )
    
    db.add(api)
    await db.commit()
    await db.refresh(api)
    
    return api


@router.get("/", response_model=List[APIResponse])
async def list_apis(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("api:list"))
):
    """List all APIs. Requires api:list permission."""
    
    # Regular users see only their APIs
    # Admins/superusers see all APIs
    if user.is_superuser:
        result = await db.execute(select(API))
    else:
        result = await db.execute(
            select(API).where(API.owner_id == user.id)
        )
    
    apis = result.scalars().all()
    return apis


@router.get("/{api_id}", response_model=APIResponse)
async def get_api(
    api_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("api:read"))
):
    """Get API by ID. Requires api:read permission."""
    
    result = await db.execute(select(API).where(API.id == api_id))
    api = result.scalar_one_or_none()
    
    if not api:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API not found"
        )
    
    # Check if user can access this API
    if api.owner_id != user.id and not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this API"
        )
    
    return api


@router.put("/{api_id}", response_model=APIResponse)
async def update_api(
    api_id: int,
    api_data: APIUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("api:update"))
):
    """Update API. Requires api:update permission."""
    
    result = await db.execute(select(API).where(API.id == api_id))
    api = result.scalar_one_or_none()
    
    if not api:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API not found"
        )
    
    # Only owner or superuser can update
    if api.owner_id != user.id and not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update your own APIs"
        )
    
    # Update fields
    for field, value in api_data.dict(exclude_unset=True).items():
        setattr(api, field, value)
    
    await db.commit()
    await db.refresh(api)
    
    return api


@router.delete("/{api_id}", status_code=status.HTTP_200_OK)
async def delete_api(
    api_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("api:delete"))
):
    """Delete API. Requires api:delete permission."""
    
    result = await db.execute(select(API).where(API.id == api_id))
    api = result.scalar_one_or_none()
    
    if not api:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API not found"
        )
    
    # Only owner or superuser can delete
    if api.owner_id != user.id and not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only delete your own APIs"
        )
    
    await db.delete(api)
    await db.commit()
    
    return {"message": f"API {api_id} deleted successfully"}
```

## Testing Protected Endpoints

### Test Script

```python
# test_protected_endpoints.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_api_without_permission(client: AsyncClient):
    """Test that users without permission can't create APIs."""
    
    # Login as viewer (no api:create permission)
    login_response = await client.post("/auth/login", json={
        "email": "viewer@example.com",
        "password": "password"
    })
    token = login_response.json()["access_token"]
    
    # Try to create API
    response = await client.post(
        "/apis",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Test API", "version": "1.0"}
    )
    
    # Should be forbidden
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_api_with_permission(client: AsyncClient):
    """Test that users with permission can create APIs."""
    
    # Login as developer (has api:create permission)
    login_response = await client.post("/auth/login", json={
        "email": "developer@example.com",
        "password": "password"
    })
    token = login_response.json()["access_token"]
    
    # Create API
    response = await client.post(
        "/apis",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Test API", "version": "1.0"}
    )
    
    # Should succeed
    assert response.status_code == 201
```

## Best Practices

### 1. Always Check Ownership + Permission

```python
# GOOD: Check both permission and ownership
@router.delete("/resources/{id}")
async def delete_resource(
    id: int,
    user = Depends(require_permission("resource:delete")),
    db = Depends(get_db)
):
    resource = await get_resource(db, id)
    
    # Permission check (done by decorator)
    # Owner check (manual)
    if resource.owner_id != user.id and not user.is_superuser:
        raise HTTPException(status_code=403)
    
    await delete(resource)
```

### 2. Use Specific Permissions

```python
# GOOD: Specific permissions
require_permission("api:create")
require_permission("api:delete")

# BAD: Too broad
require_role("admin")  # Unless you really need to restrict to admins only
```

### 3. Document Required Permissions

```python
@router.post("/apis")
async def create_api(
    user = Depends(require_permission("api:create"))
):
    """
    Create a new API.
    
    **Required Permission**: api:create
    **Available to**: admin, developer roles
    """
    pass
```

### 4. Provide Clear Error Messages

```python
from fastapi import HTTPException, status

if not has_permission:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "permission_denied",
            "required_permission": "api:create",
            "message": "You need the 'api:create' permission to perform this action"
        }
    )
```

### 5. Log Authorization Events

```python
from app.logging_config import get_logger

logger = get_logger("authorization")

@router.delete("/apis/{api_id}")
async def delete_api(
    api_id: int,
    user = Depends(require_permission("api:delete"))
):
    logger.info(
        f"User {user.id} ({user.email}) attempting to delete API {api_id}",
        extra={
            "user_id": user.id,
            "action": "DELETE_API",
            "resource_id": api_id
        }
    )
    
    # Your implementation
    pass
```

## Summary

Choose the right method for your use case:

- **Simple permission check**: Use `require_permission()` decorator
- **Role-based check**: Use `require_role()` decorator  
- **Complex logic**: Use `RBACManager` manually
- **Attribute-based**: Use `PolicyEngine`
- **Ownership**: Combine permission with manual ownership check

All methods integrate seamlessly with FastAPI's dependency injection system!
