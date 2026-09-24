---
name: invoice-wizard
description: >
  Step-by-step invoice creation wizard. Trigger when user wants to create a new invoice from
  scratch: "nowa faktura", "wystaw fakturę za kwiecień", "new invoice for april", "przygotuj
  fakturę", "create invoice".
---

# Invoice Creation Wizard

Guide the user through creating a complete invoice step by step.

## Setup

**Working directory:** the repository root (the directory containing `pyproject.toml`)
**Run commands with:** `uv run invoice <command>`

## Step 1: Determine the month

Ask the user which month, or detect from context. If they say "bieżący miesiąc" or "this month", run `date +%Y-%m` to get the current month. Resolve to `YYYY-MM` format.

Check if the month already has data:
```bash
cat data/YYYY/MM.yaml 2>/dev/null
```

If it exists, ask: "Ten miesiąc ma już dane. Chcesz je przejrzeć czy zacząć od nowa?"

## Step 2: Create month entry and show working days

```bash
uv run invoice show YYYY-MM
```

This auto-creates the YAML with calculated working days (excluding weekends and Polish holidays). Tell the user:
- How many working days the month has
- Whether there are any holidays in that month

## Step 3: Ask about leave

Ask: "Czy w tym miesiącu brałeś urlop bezpłatny?"

If yes, get the dates and add:
```bash
uv run invoice add-leave --month YYYY-MM --start YYYY-MM-DD --end YYYY-MM-DD --type unpaid
```

Show updated days worked.

## Step 4: Ask about expenses

Ask: "Czy masz dodatkowe wydatki do rozliczenia w tym miesiącu? (loty, hotel, uber, itp.)"

For each expense:
```bash
uv run invoice add-expense --month YYYY-MM --desc "DESCRIPTION" --amount AMOUNT
```

When done, ask: "Czy coś jeszcze?"

## Step 5: Show final calculation

```bash
uv run invoice show YYYY-MM
```

Present the summary clearly:
- Days worked / total
- Base salary
- Expenses total → after tax adjustment (/0.88)
- Final amount and multiplier
- Net value on invoice

Ask: "Czy wszystko się zgadza?"

## Step 6: Generate PDF

```bash
uv run invoice generate YYYY-MM
```

Ask: "Chcesz otworzyć PDF do podglądu?"
If yes: `uv run invoice preview YYYY-MM`

## Step 7: KSeF submission (optional)

Ask: "Chcesz wysłać fakturę do KSeF?"

If yes, ask which environment:
- "test" — testowe (domyślne, bezpieczne)
- "prod" — produkcyjne (wymaga potwierdzenia)

```bash
uv run invoice submit YYYY-MM --env ENV
```

After successful submit, inform about:
- KSeF number assigned
- PDF regenerated with QR code
- QR code links to KSeF verification page

## Language

Use the same language as the user (Polish or English). Default to Polish.
