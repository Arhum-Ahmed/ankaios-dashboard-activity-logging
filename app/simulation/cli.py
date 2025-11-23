# app/simulation/cli.py
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
    p.add_argument("--apply", action="store_true", help="If set, write snapshot on successful simulation (otherwise dry-run only)")
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

    if report.get("pre_check", {}).get("ok") is False:
        print("Pre-checks failed.", flush=True)
        raise SystemExit(2)

    sim = report.get("simulation")
    if not sim:
        raise SystemExit(3)

    if sim.get("success"):
        if args.apply:
            print("Simulation successful; snapshot path:", report.get("snapshot_path"))
        else:
            print("Simulation successful (dry-run). Use --apply to persist snapshot.")
        raise SystemExit(0)
    else:
        print("Simulation failed; attempting rollback...", flush=True)
        if report.get("rollback", {}).get("restored"):
            print("Rollback restored previous configuration.")
            raise SystemExit(4)
        else:
            print("No snapshot to roll back to.")
            raise SystemExit(5)

if __name__ == "__main__":
    main()
