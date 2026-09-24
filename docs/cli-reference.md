# CLI reference

All commands are run with `uv run invoice <command>`.

## invoice show

Display the invoice calculation for a month.

```bash
uv run invoice show 2026-04
```

If the month doesn't exist yet, it's auto-created with:
- Working days calculated (excluding weekends and Polish holidays)
- Base salary from `config.yaml`
- Next available invoice number

## invoice add-expense

Add an expense to a month's invoice.

```bash
uv run invoice add-expense --month 2026-04 --desc "flight Stockholm" --amount 1073.68
```

| Option | Required | Description |
|--------|----------|-------------|
| `--month` | Yes | Month in YYYY-MM format |
| `--desc` | Yes | Expense description |
| `--amount` | Yes | Amount in PLN |

Expenses are divided by 0.88 to account for the 12% ryczałt tax.

## invoice add-leave

Add an unpaid leave period.

```bash
uv run invoice add-leave --month 2026-04 --start 2026-04-11 --end 2026-04-19 --type unpaid
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--month` | Yes | — | Month in YYYY-MM format |
| `--start` | Yes | — | Start date (YYYY-MM-DD) |
| `--end` | Yes | — | End date (YYYY-MM-DD, inclusive) |
| `--type` | No | `unpaid` | Leave type |

Working days are automatically calculated (weekends and Polish holidays excluded).

## invoice generate

Generate a PDF invoice.

```bash
uv run invoice generate 2026-04
```

Output: `output/invoice_0004_2026.pdf`

## invoice preview

Generate and open the PDF in the system viewer.

```bash
uv run invoice preview 2026-04
```

## invoice generate-xml

Generate KSeF FA(3) XML.

```bash
uv run invoice generate-xml 2026-04
```

Output: `output/invoice_0004_2026.xml`

## invoice validate

Validate the XML against the FA(3) schema using `@ksefuj/validator`.

```bash
uv run invoice validate 2026-04
```

Requires `npx` (Node.js). Runs three validation layers:
1. XSD schema compliance
2. Ministry of Finance semantic rules
3. Tax calculation checks

## invoice submit

Submit the invoice to KSeF.

```bash
# Test environment (default)
uv run invoice submit 2026-04 --env test

# Production (requires confirmation)
uv run invoice submit 2026-04 --env prod

# Dry run — generate XML only, don't submit
uv run invoice submit 2026-04 --dry-run
```

| Option | Default | Description |
|--------|---------|-------------|
| `--env` | `test` | KSeF environment: `test`, `demo`, `prod` |
| `--dry-run` | `false` | Generate XML without submitting |

After successful submission:
- KSeF number is saved to the month's YAML
- PDF is regenerated with QR code
- Status changes to `submitted`

## invoice status

Check the KSeF submission status.

```bash
uv run invoice status 2026-04
```

## Status flow

```
draft → generated → submitted → confirmed
```

- **draft** — month entry created, data being collected
- **generated** — PDF has been generated
- **submitted** — sent to KSeF, KSeF number assigned
- **confirmed** — UPO received (future)
