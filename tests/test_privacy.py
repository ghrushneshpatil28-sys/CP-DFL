import torch
from torch.utils.data import DataLoader, TensorDataset
from ml.privacy import privatize
import pytest


@pytest.mark.parametrize("optimizer_type", [torch.optim.SGD, torch.optim.Adam])
def test_private_fedprox_gradient_precedes_underlying_optimizer(optimizer_type):
    from opacus.optimizers import DPOptimizer
    from ml.privacy import private_optimizer_step
    model = torch.nn.Linear(1, 1, bias=False)
    with torch.no_grad():
        model.weight.fill_(.5)
    optimizer = DPOptimizer(optimizer_type(model.parameters(), lr=.1),
        noise_multiplier=0., max_grad_norm=100., expected_batch_size=2)
    # A deterministic optimizer-boundary test, not a privacy-enabled experiment.
    model.weight.grad_sample = torch.tensor([[[1.]], [[3.]]])
    reference = torch.nn.Linear(1, 1, bias=False)
    reference.load_state_dict(model.state_dict())
    expected_optimizer = optimizer_type(reference.parameters(), lr=.1)
    reference.weight.grad = torch.tensor([[2.2]])  # mean clipped gradient 2 + mu .4 * (w .5 - global 0)
    expected_optimizer.step()
    private_optimizer_step(optimizer, model, [torch.zeros_like(model.weight)], .4)
    assert model.weight.grad.item() == pytest.approx(2.2)
    assert torch.allclose(model.weight, reference.weight)


def test_privacy_randomness_is_not_public_seed():
    def private_step():
        torch.manual_seed(42)
        model = torch.nn.Linear(2, 2)
        optimizer = torch.optim.SGD(model.parameters(), lr=.01)
        data = DataLoader(TensorDataset(torch.ones(8, 2), torch.zeros(8, dtype=torch.long)), batch_size=4,
                          generator=torch.Generator().manual_seed(42))
        model, optimizer, data, engine = privatize(model, optimizer, data,
            {"noise_multiplier": 1.1, "max_grad_norm": 1., "delta": 1e-5})
        x, y = next(iter(data))
        x.requires_grad_(True)
        loss = torch.nn.functional.cross_entropy(model(x), y) if len(y) else model(x).sum()
        loss.backward()
        assert model._module.weight.grad_sample.shape[0] == len(y)
        optimizer.step()
        result = model._module.weight.detach().clone()
        assert engine.get_epsilon(1e-5) > 0
        return result
    assert not torch.equal(private_step(), private_step())
