import pytest
from pydantic import ValidationError
from ml.config import TrainingConfig


@pytest.mark.parametrize("invalid", [
    {"rounds": 0}, {"local_epochs": -1}, {"batch_size": 1}, {"threads": 0},
    {"alpha": 0}, {"mu": -1}, {"learning_rate": float("nan")},
    {"image_size": 0}, {"dp": {"noise_multiplier": -1}},
])
def test_invalid_training_config_is_rejected(invalid):
    with pytest.raises(ValidationError):
        TrainingConfig(manifest="manifest.json", **invalid)
