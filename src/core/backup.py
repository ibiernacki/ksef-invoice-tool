"""Backup invoice artifacts to an external directory (e.g. cloud-synced folder)."""

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
DATA_DIR = PROJECT_ROOT / "data"


def backup_month(month: str, config: dict) -> Path | None:
    """Copy invoice artifacts for `month` (YYYY-MM) to the backup directory.

    Returns the destination path, or None if backup is disabled.
    Raises FileNotFoundError if backup root is configured but unreachable.
    """
    backup_cfg = config.get("backup") or {}
    if not backup_cfg.get("enabled"):
        return None

    backup_root = Path(backup_cfg["path"])
    if not backup_root.exists():
        raise FileNotFoundError(f"Backup root not found: {backup_root}")

    year, mm = month[:4], month[5:7]
    invoice_number = _read_invoice_number(year, mm)

    dest = backup_root / month
    dest.mkdir(parents=True, exist_ok=True)

    sources = [
        OUTPUT_DIR / f"invoice_{invoice_number}_{year}.pdf",
        OUTPUT_DIR / f"invoice_{invoice_number}_{year}.xml",
        OUTPUT_DIR / f"invoice_{invoice_number}_{year}.upo.xml",
        OUTPUT_DIR / f"invoice_{invoice_number}_{year}.ksef.json",
        DATA_DIR / year / f"{mm}.yaml",
    ]
    for src in sources:
        if src.exists():
            shutil.copy2(src, dest / src.name)

    return dest


def _read_invoice_number(year: str, mm: str) -> str:
    import yaml

    yaml_path = DATA_DIR / year / f"{mm}.yaml"
    with open(yaml_path) as f:
        return yaml.safe_load(f)["invoice_number"]
