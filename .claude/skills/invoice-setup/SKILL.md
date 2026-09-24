---
name: invoice-setup
description: >
  First-time setup of the invoice tool after cloning the repo: install prerequisites, create
  config.yaml with seller/buyer data, set up the KSeF token in .env, and verify everything works.
  Trigger when config.yaml or .env is missing, when a command fails with "Missing config.yaml",
  or on phrases like "skonfiguruj narzędzie", "konfiguracja", "pierwsze uruchomienie", "właśnie
  sklonowałem", "set up the invoice tool", "setup", "configure", "getting started", "onboarding".
---

# Invoice Tool Setup

Walk a new user from a fresh clone to their first test invoice. Talk to the user in their language
(Polish or English). Ask for data in small groups, not all at once.

**Working directory:** the repository root (the directory containing `pyproject.toml`)

## Step 0: Check current state

```bash
ls config.yaml .env 2>&1; command -v uv; command -v node; uname -s
```

Tell the user what is already done and what is left. If `config.yaml` already exists, show it and
ask whether to update it or keep it — never overwrite it silently.

## Step 1: Prerequisites

| Tool | Needed for | Install |
|------|------------|---------|
| Python 3.12+ and `uv` | everything | https://docs.astral.sh/uv/ (`brew install uv` on macOS) |
| pango | PDF generation (WeasyPrint) | macOS: `brew install pango`; Debian/Ubuntu: `sudo apt install libpango-1.0-0 libpangoft2-1.0-0` |
| Node.js (`npx`) | `invoice validate` only — optional | https://nodejs.org |

Ask before installing anything system-wide. Then:

```bash
uv sync
```

## Step 2: Create config.yaml

Start from the template — `config.yaml` is gitignored because it holds personal data:

```bash
cp config.example.yaml config.yaml
```

Ask for the data in these groups, then write the values into `config.yaml`:

1. **Seller (you, the JDG):** full name, NIP, business address, bank account (IBAN), BIC, bank name.
2. **Buyer (the client):** company name, registration number, EU VAT ID (with country prefix,
   e.g. `SE...`, `DE...`), address, contact person (optional — printed as the reference person).
3. **Invoice:** `base_salary` (net amount for a full month), `tax_rate` (ryczałt rate, default
   `0.12`), `payment_days`, `service_description`, `currency`.
4. **Optional:** `backup` (a folder where PDF/XML/UPO get copied after a prod submit — leave
   `enabled: false` if they don't want it) and `email.recipient` (the client's invoice inbox).

Validate before writing and point out problems instead of guessing:
- **NIP:** 10 digits, stored with `PL` prefix (e.g. `PL1234567890`). Checksum: weights
  `6,5,7,2,3,4,5,6,7` on the first 9 digits, sum mod 11 must equal the 10th digit.
- **IBAN:** Polish accounts are `PL` + 26 digits; check mod-97 (move the first 4 chars to the end,
  letters → numbers A=10…Z=35, result mod 97 must be 1).
- **Buyer VAT ID:** must start with a 2-letter EU country code. This tool issues reverse-charge
  (NP) invoices for EU B2B clients — if the buyer is Polish or outside the EU, warn that the XML
  (`P_12 = "np I"`, `P_18A`) will not fit and the tool needs changes.

Show the final `config.yaml` to the user and ask them to confirm.

## Step 3: KSeF tokens (.env)

- **Test environment** needs no token — the tool generates a self-signed test certificate.
- **Production** needs `KSEF_TOKEN`. Point the user to `docs/ksef-setup.md` (log in at
  https://ksef.mf.gov.pl, generate a token with invoice-sending permissions; it is shown only once).
- **Optional:** `KSEF_READ_INVOICES_TOKEN` — a read-only token for the `invoice-list-ksef` skill.

Tokens are secrets: **do not ask the user to paste them into the chat.** Have them add the lines
themselves by typing in the Claude Code prompt:

```
! echo "KSEF_TOKEN=<token>" >> .env
```

Then confirm only that the variable exists, without printing its value:

```bash
grep -c '^KSEF_TOKEN=' .env
```

If the user has no production token yet, skip this — they can finish setup on the test environment.

## Step 4: Verify

```bash
uv run pytest -q
uv run invoice show $(date +%Y-%m)
uv run invoice preview $(date +%Y-%m)     # opens the PDF — ask the user to check their data on it
uv run invoice generate-xml $(date +%Y-%m)
uv run invoice validate $(date +%Y-%m)    # only if Node.js is installed
```

Optionally do a full dry run on the KSeF test environment (uses synthetic data, safe):

```bash
uv run invoice submit $(date +%Y-%m) --env test
```

`show` creates `data/YYYY/MM.yaml` for the current month. If the user doesn't want a real invoice
for this month yet, tell them they can delete that file.

## Step 5: Wrap up

Summarize what was configured and what (if anything) is still missing, e.g. the production token.
Then show the day-to-day flow — the `invoice-wizard` skill ("nowa faktura za <miesiąc>") guides
through creating a monthly invoice, and `invoice-manage` handles expenses, leave, generate and submit.
