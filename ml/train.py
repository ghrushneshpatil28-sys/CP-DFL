import argparse
import json
from pathlib import Path
from ml.dataset import ROOT
from ml.engine import run_experiment
from ml.config import TrainingConfig
from pydantic import ValidationError


def main():
    parser = argparse.ArgumentParser(description="Canonical centralized/FedAvg/FedProx ResNet18 training")
    parser.add_argument("--algorithm", choices=["centralized", "fedavg", "fedprox"], default="centralized")
    parser.add_argument("--manifest", default=str(ROOT / "ml/data/manifest.json"))
    parser.add_argument("--output", required=True)
    parser.add_argument("--rounds", type=int, default=10, help="Centralized epochs or federated rounds")
    parser.add_argument("--local-epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--learning-rate", type=float, default=.001)
    parser.add_argument("--optimizer", choices=["adam", "sgd"], default="adam")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--alpha", type=float, default=.5)
    parser.add_argument("--mu", type=float, default=.01)
    parser.add_argument("--patience", type=int, default=3)
    parser.add_argument("--pretrained", action="store_true")
    parser.add_argument("--dp", action="store_true")
    parser.add_argument("--secure-aggregation", action="store_true", help="Flower SecAgg+ with three process-isolated hospitals")
    parser.add_argument("--noise-multiplier", type=float, default=1.1)
    parser.add_argument("--max-grad-norm", type=float, default=1.)
    parser.add_argument("--delta", type=float, default=1e-5)
    parser.add_argument("--target-epsilon", type=float)
    args = vars(parser.parse_args())
    output = args.pop("output")
    args["dp"] = {"enabled": args["dp"], **{k: args.pop(k) for k in ["noise_multiplier", "max_grad_norm", "delta", "target_epsilon"]}}
    try:
        config = TrainingConfig.model_validate(args).model_dump()
        result = run_experiment(config, Path(output))
    except (ValidationError, ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
