# Architecture

## Project structure

```
invoice-tool/
├── src/
│   ├── cli.py                  # Typer CLI — thin wrapper over core
│   ├── core/
│   │   ├── models.py           # Dataclasses: Expense, LeaveEntry, MonthEntry, InvoiceData
│   │   ├── calculator.py       # Invoice calculation logic
│   │   ├── workdays.py         # Polish working days + public holidays
│   │   ├── store.py            # YAML persistence (data/{YEAR}/{MM}.yaml)
│   │   ├── pdf_generator.py    # WeasyPrint + Jinja2 → PDF
│   │   ├── ksef_xml.py         # FA(3) XML generation with lxml
│   │   └── ksef_client_wrapper.py  # ksef2 library wrapper
│   └── templates/
│       ├── invoice.html        # Jinja2 invoice template
│       └── invoice.css         # Invoice styling
├── data/                       # Monthly YAML data (committed to git)
├── output/                     # Generated PDF + XML (committed to git)
├── tests/                      # pytest tests
├── config.yaml                 # Seller, buyer, rates configuration
├── .env                        # KSeF token (gitignored)
└── .claude/skills/             # Claude Code skills
```

## Core design principle

All business logic lives in `src/core/` with no dependencies on CLI frameworks or web frameworks. The CLI (`src/cli.py`) is a thin wrapper that parses arguments and calls core functions.

This makes it easy to add alternative interfaces:

```
CLI (typer)  ──→  core/calculator.py
                  core/store.py         ← same functions
API (FastAPI) ──→ core/pdf_generator.py
                  core/ksef_client_wrapper.py
```

## Data flow

```
1. User input (CLI/skill)
       ↓
2. store.get_or_create_month() → data/YYYY/MM.yaml
       ↓
3. calculator.calculate_invoice() → InvoiceData
       ↓
4. pdf_generator.generate_pdf() → output/invoice_XXXX_YYYY.pdf
   ksef_xml.generate_invoice_xml() → output/invoice_XXXX_YYYY.xml
       ↓
5. ksef_client_wrapper.submit_invoice() → KSeF number + UPO
       ↓
6. pdf_generator.generate_pdf(ksef_number=...) → PDF with QR code
```

## Month YAML format

```yaml
month: "2026-04"
days_total: 21
base_salary: 20000.0
invoice_number: "0004"
issued_date: "2026-04-30"
ref_person: "Anna Svensson"
days_worked: 16
status: draft
ksef_id: null
leave:
  - start: "2026-04-11"
    end: "2026-04-19"
    type: unpaid
    working_days: 5
expenses:
  - description: flight Stockholm
    amount: 1073.68
  - description: uber
    amount: 43.79
```

## Calculation formulas

```
work_salary     = (days_worked / days_total) × base_salary
additional_gross = sum(expenses) / 0.88
final_amount    = work_salary + additional_gross
multiplier      = final_amount / base_salary
net_value       = round(base_salary × multiplier)
```

The multiplier is used as the "quantity" on the invoice line item, with base_salary as the unit price. This matches the original Excel-based workflow.

## KSeF FA(3) XML

The XML follows the official FA(3) schema (`http://crd.gov.pl/wzor/2025/06/25/13775/`).

Key elements for our reverse charge EU B2B invoices:
- `Podmiot2/DaneIdentyfikacyjne`: uses `KodUE` + `NrVatUE` (not NIP)
- `FaWiersz/P_12`: `np I` (intracommunity non-taxable)
- `Fa/P_13_11`: net amount for NP transactions
- `Adnotacje/P_18A`: `1` (intracommunity reverse charge applies)

## Future: Web API

The core module is ready for a FastAPI wrapper:
- `POST /invoices/{month}/expenses` → add_expense()
- `GET /invoices/{month}` → get_or_create_month() + calculate_invoice()
- `POST /invoices/{month}/generate` → generate_pdf()
- `POST /invoices/{month}/submit` → submit_invoice()

Deployment: Docker container → Kubernetes.
