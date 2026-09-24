import json
import os
import sys
import subprocess
from pathlib import Path

# When running as a cron script copied elsewhere (e.g. ~/.hermes/scripts/),
# set INVOICE_TOOL_ROOT so we can find the repo to run 'uv run' correctly.
PROJECT_ROOT = Path(os.environ.get("INVOICE_TOOL_ROOT", Path(__file__).resolve().parent.parent))
sys.path.append(str(PROJECT_ROOT))

SEEN_FILE = PROJECT_ROOT / "data" / "ksef_seen.json"

def load_seen():
    if SEEN_FILE.exists():
        with open(SEEN_FILE, "r") as f:
            try:
                content = json.load(f)
                return set(content) if isinstance(content, list) else set()
            except json.JSONDecodeError:
                return set()
    return set()

def save_seen(seen_set):
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen_set), f, indent=2)

def main():
    seen = load_seen()
    
    # Use absolute path to the project's list_ksef.py script
    script_path = PROJECT_ROOT / "scripts" / "list_ksef.py"
    
    cmd = [
        "uv", "run", "python", str(script_path),
        "--role", "buyer",
        "--days", "7",
        "--json"
    ]
    
    # Run from the project root so uv finds the pyproject.toml
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error calling list_ksef.py: {result.stderr}", file=sys.stderr)
        sys.exit(1)
        
    try:
        invoices = json.loads(result.stdout)
    except json.JSONDecodeError:
        return
    
    new_invoices = []
    for inv in invoices:
        ksef_num = inv.get("ksef_number")
        if ksef_num and ksef_num not in seen:
            new_invoices.append(inv)
            seen.add(ksef_num)
    
    if not new_invoices:
        return

    new_invoices.sort(key=lambda x: x["invoicing_date"])

    lines = [f"🔔 *Found {len(new_invoices)} new cost invoice(s) in KSeF*:\n"]
    for inv in new_invoices:
        lines.append(
            f"📅 {inv['issue_date'].split('T')[0]} | *{inv['gross_amount']:.2f} {inv['currency']}*\n"
            f"👤 {inv['seller_name']} (NIP: {inv['seller_nip']})\n"
            f"📄 `{inv['invoice_number']}`\n"
            f"🔗 `{inv['ksef_number']}`\n"
        )
    
    print("\n".join(lines))
    save_seen(seen)

if __name__ == "__main__":
    main()
