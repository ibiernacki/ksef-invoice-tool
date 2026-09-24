# Quick start

Get from zero to your first invoice in 5 minutes.

## 1. Install

```bash
git clone git@github.com:ibiernacki/ksef-invoice-tool.git
cd ksef-invoice-tool
uv sync
brew install pango  # macOS only, needed for PDF generation
```

## 2. Configure

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` with your seller/buyer data and base salary. (In Claude Code you can instead
say "set up the invoice tool" — the `invoice-setup` skill will ask for everything and write the file.)

Create `.env` for KSeF:
```bash
echo "KSEF_TOKEN=your-ksef-token" > .env
```

## 3. Create your first invoice

```bash
# This auto-creates the month with calculated working days
uv run invoice show 2026-04
```

Output:
```
==================================================
  Invoice 0004/2026
  Month: 2026-04
==================================================
  Days worked:      21/21
  Base salary:       20000 PLN
  Work salary:    20000.00 PLN

  Final amount:   20000.00 PLN
  Multiplier:       1.0000
  Net value:         20000 PLN
  Status:           draft
==================================================
```

## 4. Add expenses and leave

```bash
uv run invoice add-expense --month 2026-04 --desc "flight Stockholm" --amount 1073.68
uv run invoice add-expense --month 2026-04 --desc "hotel" --amount 839.91
uv run invoice add-leave --month 2026-04 --start 2026-04-11 --end 2026-04-19 --type unpaid
```

## 5. Review and generate

```bash
# Review calculation
uv run invoice show 2026-04

# Generate and open PDF
uv run invoice preview 2026-04
```

## 6. Submit to KSeF

```bash
# Test environment first
uv run invoice submit 2026-04 --env test

# When ready for production
uv run invoice submit 2026-04 --env prod
```

After submission, the PDF is automatically regenerated with a KSeF QR code.

## Monthly workflow

Each month, the typical flow is:

1. `invoice show YYYY-MM` — creates the month, shows working days
2. `invoice add-expense` — add any business expenses
3. `invoice add-leave` — add any unpaid leave
4. `invoice show YYYY-MM` — verify calculation
5. `invoice preview YYYY-MM` — check PDF
6. `invoice submit YYYY-MM --env prod` — submit to KSeF

Or, if using Claude Code, just say: "Przygotuj fakturę za kwiecień"
