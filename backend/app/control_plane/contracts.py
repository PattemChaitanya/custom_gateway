"""Versioned platform contract for the mini-cloud implementation."""

from pydantic import BaseModel, Field


class ContractGuarantees(BaseModel):
    service_registration: str = "registry stores service instances with metadata and weighted routing hints"
    routing: str = "requests are routed only to healthy instances from discovery"
    auth: str = "route-level auth policy references are externally configured"
    rate_limits: str = "route-level rate limit policy references are externally configured"
    metrics: str = "RED metrics (rate, errors, duration) are emitted for routed requests"
    scaling_simulation: str = "autoscaler uses queue depth and latency with cooldown and hysteresis"


class ContractTradeoffs(BaseModel):
    definition_first: str = "upfront contract design slows initial coding but prevents repeated redesign"
    state_management: str = "registry/scheduler state increases complexity but enables reliable failover"
    coupled_validation: str = "tight routing-discovery integration reduces abstraction but speeds end-to-end validation"


class PlatformContract(BaseModel):
    version: str = Field(default="mini-cloud/v1")
    guarantees: ContractGuarantees = Field(default_factory=ContractGuarantees)
    tradeoffs: ContractTradeoffs = Field(default_factory=ContractTradeoffs)


PLATFORM_CONTRACT = PlatformContract()
