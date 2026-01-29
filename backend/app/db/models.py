from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func, JSON, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base

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


