# deployment/cli.py
"""Small CLI to run simulation and apply config (saves snapshot on success)."""

import argparse
import yaml
import json
from .validator_service import ValidatorService


def main():
    p = argparse.ArgumentParser(prog="ankaios-deploy-sim", description="Simulate and snapshot/rollback configs")
    p.add_argument("--config", "-c", required=True, help="Path to YAML config file")
    p.add_argument("--base-dir", default=".", help="Base directory for snapshots (.ankaios_history)")
    p.add_argument("--cpu", type=float, default=None, help="Cluster CPU capacity override")
    p.add_argument("--memory", type=float, default=None, help="Cluster memory capacity override")
    args = p.parse_args()

    with open(args.config, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    cluster = None
    if args.cpu is not None or args.memory is not None:
        cluster = {}
        if args.cpu is not None:
            cluster["cpu"] = args.cpu
        if args.memory is not None:
            cluster["memory"] = args.memory

    svc = ValidatorService(base_dir=args.base_dir)
    report = svc.apply_config(cfg, cluster_capacity=cluster)
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
