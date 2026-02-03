from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func, JSON, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property

# use SQLAlchemy 2.0 compatible declarative_base import
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(320), unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    # optional comma-separated roles field for simple RBAC (e.g. 'admin,editor')
    roles = Column(String, default='', nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False)

    user = relationship("User", back_populates="refresh_tokens")


class OTP(Base):
    __tablename__ = "otps"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(320), nullable=False, index=True)
    otp_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, default=0)
    consumed = Column(Boolean, default=False)
    transport = Column(String, nullable=True)  # e.g. 'email' or 'sms'


class API(Base):
    __tablename__ = "apis"
    __table_args__ = (UniqueConstraint('name', 'version', name='uq_api_name_version'),)

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    version = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    # canonical configuration for the API (paths, defaults, etc.)
    # optional API type (rest/graphql) stored as a simple string for quick queries
    type = Column(String, nullable=True)
    # resource column can store structured resource metadata (JSON)
    resource = Column(JSON, nullable=True)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    schemas = relationship("Schema", back_populates="api", cascade="all, delete-orphan")
    auth_policies = relationship("AuthPolicy", back_populates="api", cascade="all, delete-orphan")
    rate_limits = relationship("RateLimit", back_populates="api", cascade="all, delete-orphan")
    connectors = relationship("Connector", back_populates="api", cascade="all, delete-orphan")


class Schema(Base):
    __tablename__ = "schemas"

    id = Column(Integer, primary_key=True, index=True)
    api_id = Column(Integer, ForeignKey("apis.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    # store JSON Schema or raw schema text
    definition = Column(JSON, nullable=True)
    raw = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    api = relationship("API", back_populates="schemas")


class AuthPolicy(Base):
    __tablename__ = "auth_policies"

    id = Column(Integer, primary_key=True, index=True)
    api_id = Column(Integer, ForeignKey("apis.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False)  # e.g. 'apiKey', 'oauth2', 'jwt'
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    api = relationship("API", back_populates="auth_policies")


class RateLimit(Base):
    __tablename__ = "rate_limits"

    id = Column(Integer, primary_key=True, index=True)
    api_id = Column(Integer, ForeignKey("apis.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    key_type = Column(String, nullable=False, default='global')  # per-key, per-ip, global
    limit = Column(Integer, nullable=False)
    window_seconds = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    api = relationship("API", back_populates="rate_limits")


class Connector(Base):
    __tablename__ = "connectors"

    id = Column(Integer, primary_key=True, index=True)
    api_id = Column(Integer, ForeignKey("apis.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False)  # e.g. 'http', 'lambda', 'kafka'
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    api = relationship("API", back_populates="connectors")


class Environment(Base):
    __tablename__ = "environments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    slug = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, nullable=False, unique=True, index=True)
    label = Column(String, nullable=True)
    scopes = Column(String, nullable=True)  # comma-separated scopes
    revoked = Column(Boolean, default=False)
    environment_id = Column(Integer, ForeignKey("environments.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0)
    metadata_json = Column(JSON, name="metadata", nullable=True)

    environment = relationship("Environment")


class ModuleMetadata(Base):
    __tablename__ = "module_metadata"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    version = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    # 'metadata' is a reserved attribute on Declarative classes; store JSON here
    metadata_json = Column(JSON, name="metadata", nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Secret(Base):
    __tablename__ = "secrets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    value = Column(Text, nullable=False)  # Encrypted value
    description = Column(Text, nullable=True)
    tags = Column(String, nullable=True)  # comma-separated tags
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Hybrid property for test compatibility - works both in Python and SQL
    @hybrid_property
    def key(self):
        """Alias for 'name' attribute for test compatibility."""
        return self.name
    
    @key.expression
    def key(cls):
        """SQL expression for key (maps to name column)."""
        return cls.name
    
    @hybrid_property
    def encrypted_value(self):
        """Alias for 'value' attribute for test compatibility."""
        return self.value
    
    @encrypted_value.expression
    def encrypted_value(cls):
        """SQL expression for encrypted_value (maps to value column)."""
        return cls.value


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String, nullable=False, index=True)  # CREATE, UPDATE, DELETE, LOGIN, etc.
    resource_type = Column(String, nullable=True, index=True)  # API, User, Key, etc.
    resource_id = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    metadata_json = Column(JSON, name="metadata", nullable=True)
    status = Column(String, nullable=True)  # success, failure
    error_message = Column(Text, nullable=True)

    user = relationship("User")


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    metric_type = Column(String, nullable=False, index=True)  # request, latency, error
    endpoint = Column(String, nullable=True, index=True)
    method = Column(String, nullable=True)
    status_code = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    api_id = Column(Integer, ForeignKey("apis.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    metadata_json = Column(JSON, name="metadata", nullable=True)

    api = relationship("API")
    user = relationship("User")


class BackendPool(Base):
    __tablename__ = "backend_pools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    api_id = Column(Integer, ForeignKey("apis.id", ondelete="CASCADE"), nullable=True, index=True)
    algorithm = Column(String, nullable=False, default='round_robin')  # round_robin, least_connections, weighted
    backends = Column(JSON, nullable=False)  # List of backend URLs with weights
    health_check_url = Column(String, nullable=True)
    health_check_interval = Column(Integer, default=30)  # seconds
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    api = relationship("API")


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    resource = Column(String, nullable=False, index=True)  # e.g., 'api', 'user', 'key'
    action = Column(String, nullable=False, index=True)  # e.g., 'create', 'read', 'update', 'delete'
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    permissions = Column(JSON, nullable=True)  # List of permission IDs or names
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    role = relationship("Role")


class ModuleScript(Base):
    __tablename__ = "module_scripts"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("module_metadata.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    script_type = Column(String, nullable=False)  # python, javascript, bash, etc.
    content = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    module = relationship("ModuleMetadata")


