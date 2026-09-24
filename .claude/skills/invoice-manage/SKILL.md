---
name: invoice-manage
description: >
  Manage invoices: add/remove expenses, add/remove leave, show calculations, generate PDF/XML,
  validate, submit to KSeF, check status. Trigger on any invoice-related request in Polish or
  English: "faktura", "invoice", "dodaj wydatek", "add expense", "urlop", "leave", "wygeneruj",
  "generate", "wyślij", "submit", "pokaż", "show", "status", "lista faktur".
---

# Invoice Management

You help the user manage their monthly invoices. All operations use the `invoice` CLI tool.

## Setup

**Working directory:** the repository root (the directory containing `pyproject.toml`)
**Run commands with:** `uv run invoice <command>`

## Resolving the month

The user may specify months in various ways. Always resolve to `YYYY-MM` format:
- "kwiecień", "april" → `YYYY-04` (use current year)
- "kwiecień 2026" → `2026-04`
- "ten miesiąc", "bieżący miesiąc", "this month" → run `date +%Y-%m` to get the current month
- "poprzedni miesiąc", "last month" → compute from current date
- If no month specified, ask the user

## Operations

### Show / Preview

User says: "pokaż kwiecień", "show april", "co mam w kwietniu"

```bash
uv run invoice show YYYY-MM
```

### Add expense

User says: "dodaj lot za 1200 zł do kwietnia", "add flight 1200 PLN to april"

Parse: description and amount from natural language. Then:
```bash
uv run invoice add-expense --month YYYY-MM --desc "DESCRIPTION" --amount AMOUNT
```

After adding, run `uv run invoice show YYYY-MM` to display updated calculation.

### Add leave

User says: "urlop od 11 do 19 kwietnia", "leave april 11-19", "bezpłatny urlop 5 dni w kwietniu"

Parse start and end dates. Then:
```bash
uv run invoice add-leave --month YYYY-MM --start YYYY-MM-DD --end YYYY-MM-DD --type unpaid
```

After adding, run `uv run invoice show YYYY-MM` to display updated days.

### Remove expense

User says: "usuń lot z kwietnia", "remove flight from april"

1. Read the YAML file: `data/YYYY/MM.yaml`
2. Find the matching expense by description (fuzzy match)
3. Remove it from the `expenses` list using the Edit tool
4. Run `uv run invoice show YYYY-MM` to confirm

### Remove leave

User says: "usuń urlop z kwietnia", "remove leave from april"

1. Read the YAML file: `data/YYYY/MM.yaml`
2. Remove the leave entry from `leave` list using the Edit tool
3. Recalculate `days_worked`: set it to `days_total` minus remaining leave working days
4. Run `uv run invoice show YYYY-MM` to confirm

### Generate PDF

User says: "wygeneruj PDF", "generate invoice", "stwórz fakturę"

```bash
uv run invoice generate YYYY-MM
```

To also open the PDF:
```bash
uv run invoice preview YYYY-MM
```

### Generate XML + Validate

User says: "wygeneruj XML", "zwaliduj fakturę"

```bash
uv run invoice generate-xml YYYY-MM
uv run invoice validate YYYY-MM
```

### Submit to KSeF

User says: "wyślij do KSeF", "submit to KSeF"

**Always confirm environment with the user before submitting.**

For test:
```bash
uv run invoice submit YYYY-MM --env test
```

For production (requires confirmation):
```bash
uv run invoice submit YYYY-MM --env prod
```

Dry run (validate only):
```bash
uv run invoice submit YYYY-MM --dry-run
```

After submit, the PDF is auto-regenerated with KSeF QR code.

### Check status

User says: "sprawdź status", "status faktury"

```bash
uv run invoice status YYYY-MM
```

### List all invoices

User says: "pokaż wszystkie faktury", "lista faktur", "list invoices"

```bash
ls data/
ls data/YYYY/
```

Show each month's status by reading the YAML files.

## After every operation

Always show the result to the user. For data-changing operations (add/remove), run `invoice show` afterward to display the updated calculation.

## Language

Respond in the same language the user uses (Polish or English).
