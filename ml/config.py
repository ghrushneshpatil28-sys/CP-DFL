"""Shared validation for API, command-line and queued training configurations."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DPConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    enabled: bool = False
    delta: float = Field(default=1e-5, gt=0, lt=.01)
    noise_multiplier: float = Field(default=1.1, ge=.1, le=20)
    max_grad_norm: float = Field(default=1., gt=0, le=100)
    target_epsilon: float | None = Field(default=None, gt=0, le=100)


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    algorithm: Literal["centralized", "fedavg", "fedprox"] = "fedavg"
    rounds: int = Field(default=3, ge=1, le=100)
    local_epochs: int = Field(default=1, ge=1, le=20)
    batch_size: int = Field(default=16, ge=2, le=128)
    image_size: Literal[64, 128, 224] = 224
    learning_rate: float = Field(default=.001, gt=0, le=.1)
    optimizer: Literal["adam", "sgd"] = "adam"
    seed: int = Field(default=42, ge=0, le=2147483647)
    alpha: float = Field(default=.5, gt=0, le=100)
    mu: float = Field(default=.01, ge=0, le=10)
    patience: int = Field(default=3, ge=1, le=100)
    pretrained: bool = False
    secure_aggregation: bool = False
    dp: DPConfig = Field(default_factory=DPConfig)

    @model_validator(mode="after")
    def secure_federated_only(self):
        if self.secure_aggregation and self.algorithm == "centralized":
            raise ValueError("Secure aggregation requires FedAvg or FedProx and three hospital clients")
        return self


class TrainingConfig(ExperimentConfig):
    manifest: str = Field(min_length=1)
    threads: int = Field(default=4, ge=1, le=64)
