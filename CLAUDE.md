# Invoice Tool

Polish invoice automation tool with KSeF 2.0 integration.

## Project context

- Seller: Polish JDG (sole proprietorship) on ryczałt (default 12%)
- Buyer: a single EU B2B client, reverse charge (NP)
- One invoice per month for "Software development services"
- Seller/buyer data and base salary live in `config.yaml` (gitignored; template: `config.example.yaml`)
- First-time setup: if `config.yaml` or `.env` is missing, use the `invoice-setup` skill

## How to run

From the repository root:

```bash
uv run invoice <command> [args]
```

## CLI commands

| Command | Example |
|---------|---------|
| `show <YYYY-MM>` | `invoice show 2026-04` |
| `add-expense --month --desc --amount` | `invoice add-expense --month 2026-04 --desc "flight" --amount 1073.68` |
| `add-leave --month --start --end` | `invoice add-leave --month 2026-04 --start 2026-04-11 --end 2026-04-19` |
| `generate <YYYY-MM>` | `invoice generate 2026-04` |
| `preview <YYYY-MM>` | `invoice preview 2026-04` (opens PDF) |
| `generate-xml <YYYY-MM>` | `invoice generate-xml 2026-04` |
| `validate <YYYY-MM>` | `invoice validate 2026-04` (requires npx) |
| `submit <YYYY-MM> [--env test\|prod]` | `invoice submit 2026-04 --env test` |
| `status <YYYY-MM>` | `invoice status 2026-04` |

## Data storage

- Monthly data: `data/{YEAR}/{MM}.yaml` (auto-created on first access)
- Output: `output/invoice_{NUMBER}_{YEAR}.{pdf,xml}`
- Config: `config.yaml` (seller, buyer, rates) — gitignored, never commit
- KSeF token: `.env` (never commit)

## Key conventions

- Month format: always `YYYY-MM` (e.g., `2026-04`)
- Invoice numbers: `0001`-`0012` per year, zero-padded
- Working days: Mon-Fri minus Polish public holidays (including movable: Easter, Corpus Christi)
- Expense gross-up: `expenses / 0.88` (accounts for 12% ryczałt)
- Multiplier: `final_amount / base_salary` (used as quantity on invoice)
- Status flow: `draft` → `generated` → `submitted` → `confirmed`

## Architecture

```
src/core/     — business logic (no CLI/framework dependencies)
src/cli.py    — thin Typer wrapper over core
src/templates/ — Jinja2 HTML/CSS for PDF
```

## KSeF integration

- Library: `ksef2` (Python SDK for KSeF 2.0 API)
- Test env: self-signed certificate via `with_test_certificate(nip=...)`
- Prod env: token from `.env` via `with_token(ksef_token=..., nip=...)`
- XML schema: FA(3) — `http://crd.gov.pl/wzor/2025/06/25/13775/`
- Validation: `npx @ksefuj/validator <file.xml>`
- QR Code I format: `https://qr.ksef.mf.gov.pl/invoice/{NIP}/{DD-MM-RRRR}/{SHA256_BASE64URL}`

## Removing entries

To remove an expense or leave from a month, edit the YAML file directly:
`data/{YEAR}/{MM}.yaml` — delete the entry from `expenses:` or `leave:` list, then recalculate `days_worked` if leave was removed (`days_worked = days_total - sum of leave working_days`).
