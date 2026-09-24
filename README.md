# ksef-invoice-tool

Automated invoice generation with KSeF 2.0 integration for Polish sole proprietorship (JDG).

Generates professional PDF invoices, FA(3) XML for KSeF, and handles the full submission flow — from expense tracking to QR-verified e-invoices.

## Features

- Monthly invoice calculation (base salary + expenses / 0.88 for ryczałt)
- Polish working days with public holidays (including movable: Easter, Corpus Christi)
- Leave tracking with automatic days recalculation
- Professional PDF generation (WeasyPrint + Jinja2)
- KSeF 2.0 FA(3) XML generation and submission
- QR code verification (KSeF Code I format)
- Offline validation with `@ksefuj/validator`
- Claude Code skills for natural language interaction

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- pango (for PDF generation): `brew install pango`
- Node.js (for XML validation): `npx @ksefuj/validator`

## Installation

```bash
git clone git@github.com:ibiernacki/ksef-invoice-tool.git
cd ksef-invoice-tool
uv sync
```

### Configuration

The easiest way: open the repo in [Claude Code](https://claude.com/claude-code) and say
**"skonfiguruj narzędzie"** / **"set up the invoice tool"** — the `invoice-setup` skill walks you
through everything below.

Manually:
```bash
cp config.example.yaml config.yaml   # then fill in seller/buyer data and base salary
echo "KSEF_TOKEN=your-production-token" > .env   # only needed for --env prod
```

`config.yaml`, `.env`, `data/` and `output/` are gitignored — your personal data never gets committed.

## Quick start

```bash
# Show invoice for April 2026 (auto-creates month entry)
uv run invoice show 2026-04

# Add expenses
uv run invoice add-expense --month 2026-04 --desc "flight Stockholm" --amount 1073.68
uv run invoice add-expense --month 2026-04 --desc "uber" --amount 43.79

# Add leave
uv run invoice add-leave --month 2026-04 --start 2026-04-11 --end 2026-04-19

# Review calculation
uv run invoice show 2026-04

# Generate PDF
uv run invoice preview 2026-04

# Submit to KSeF (test environment)
uv run invoice submit 2026-04 --env test
```

## CLI reference

| Command | Description |
|---------|-------------|
| `invoice show <month>` | Show calculation summary |
| `invoice add-expense --month --desc --amount` | Add an expense |
| `invoice add-leave --month --start --end` | Add leave period |
| `invoice generate <month>` | Generate PDF |
| `invoice preview <month>` | Generate and open PDF |
| `invoice generate-xml <month>` | Generate KSeF FA(3) XML |
| `invoice validate <month>` | Validate XML with @ksefuj/validator |
| `invoice submit <month> [--env test\|prod] [--dry-run]` | Submit to KSeF |
| `invoice status <month>` | Check KSeF submission status |

Month format: `YYYY-MM` (e.g., `2026-04`)

## Claude Code integration

When using Claude Code in this project, you can interact with invoices using natural language:

| English | Polish |
|---------|--------|
| Set up the invoice tool | Skonfiguruj narzędzie |
| Add a flight for 1200 PLN to April | Dodaj lot za 1200 zł do kwietnia |
| Leave from April 11 to April 19 | Urlop od 11 do 19 kwietnia |
| Generate the April invoice | Wygeneruj fakturę za kwiecień |
| Submit to KSeF | Wyślij do KSeF |
| Show all invoices | Pokaż wszystkie faktury |

See [docs/](docs/) for detailed documentation.

## Documentation

- [Quick start](docs/quickstart.md) — from installation to first invoice
- [CLI reference](docs/cli-reference.md) — all commands with examples
- [KSeF setup](docs/ksef-setup.md) — token generation, environments, testing
- [Architecture](docs/architecture.md) — project structure and design decisions
