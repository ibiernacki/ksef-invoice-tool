---
name: invoice-list-ksef
description: List invoices from KSeF (Polish national e-invoicing system) — purchase invoices we received or sales invoices we issued. Use when the user wants to see what's in KSeF, browse received/cost invoices, check newly issued invoices, or build automation that watches for new purchase invoices. Triggers on PL/EN phrases like "pokaż faktury z ksef", "list ksef invoices", "faktury kosztowe", "co kupiłem w marcu", "moje faktury sprzedaży", "received invoices", "what new invoices arrived".
---

# Invoice list (KSeF read-only)

Lists invoice metadata from KSeF using the read-only token `KSEF_READ_INVOICES_TOKEN`. **Read-only** — never writes, submits, or modifies anything.

## When to use

- "pokaż faktury z KSeF", "lista faktur w ksef", "wszystkie faktury"
- "faktury kosztowe", "faktury zakupowe", "co otrzymałem", "list received invoices", "purchase invoices"
- "moje faktury sprzedaży", "co wystawiłem w KSeF", "issued invoices", "sales invoices"
- "co nowego w ksef", "nowe faktury", "any new invoices since X"
- "pokaż faktury z marca/Q1/ostatniego kwartału"
- Any time the user asks about invoices stored in KSeF (as opposed to local files in `data/`)

**Default assumption:** if the user says "faktury" / "invoices" without qualifying, they usually mean **received** (`role=buyer`) — those are the ones that arrive without their action and matter for accounting. Confirm only if ambiguous.

## How it works

```bash
uv run python scripts/list_ksef.py [options]
```

Backed by `src/core/ksef_client_wrapper.py:list_invoices()` which:
- Authenticates with `KSEF_READ_INVOICES_TOKEN` against `Environment.PRODUCTION`
- Splits date windows >85 days into multiple queries (KSeF caps at 3 calendar months per call)
- Paginates internally and deduplicates by `ksef_number`

## Options

| Flag | Default | Notes |
|---|---|---|
| `--role` | `buyer` | `buyer` = received, `seller` = issued, plus `third_subject`, `authorized_subject` |
| `--from YYYY-MM-DD` | (none) | Start date; if missing, uses `--days` lookback |
| `--to YYYY-MM-DD` | now | End date |
| `--days N` | `30` | Lookback when `--from` not given |
| `--date-type` | `invoicing_date` | also `issue_date`, `permanent_storage` |
| `--sort` | `desc` | `asc`/`desc` by invoicing_date |
| `--json` | off | machine-readable output (use for automation) |

**The script intentionally has no counterparty/amount/text filter flags.** The script pulls raw data; you filter it in conversation. This is deliberate — counterparty names from users are often paraphrased ("The Shire" vs `"TheShire sp. z o.o."`, "biuro księgowe" vs `"BIURO USŁUG KSIĘGOWO-PODATKOWYCH 'VOG'"`), and a hard-coded substring matcher commits prematurely to one algorithm. You can do better fuzzy/semantic matching contextually.

## Common requests → commands

| User says | Command |
|---|---|
| "pokaż faktury kosztowe" / "list received invoices" | `uv run python scripts/list_ksef.py` |
| "faktury z ostatnich 3 miesięcy" | `uv run python scripts/list_ksef.py --days 90` |
| "co kupiłem w marcu 2026" | `uv run python scripts/list_ksef.py --from 2026-03-01 --to 2026-03-31` |
| "moje faktury sprzedaży w tym roku" | `uv run python scripts/list_ksef.py --role seller --from 2026-01-01` |
| "wszystkie faktury z Q1" | `uv run python scripts/list_ksef.py --from 2026-01-01 --to 2026-03-31` |
| "machine-readable output for tooling" | append `--json` to any of the above |

## Filtering by counterparty (or other criteria)

When the user asks "faktury z The Shire", "co kupiłem od EURO-NET", "od księgowej", "od kontrahenta o NIP 5252457115", etc.:

1. Run the script with `--json` for the appropriate date window (no party flag — there isn't one).
2. Filter the returned list yourself, using context:
   - **Numeric NIP (10 digits)** → exact match on `seller_nip` (or `buyer_id` if `role=seller`).
   - **Name** → fuzzy match: case-insensitive, ignore whitespace and punctuation differences. `"The Shire"` should match `"TheShire sp. z o.o."`. `"VOG"` should match `"BIURO USŁUG KSIĘGOWO-PODATKOWYCH 'VOG'"`.
   - **Ambiguous** ("biuro księgowe", "ten z mieszkania") → match semantically; if multiple sellers fit or none clearly do, ask the user to disambiguate rather than guess.
3. Show the filtered subset in the standard tabular format (date, invoice_number, net/vat/gross, party).

For one-off CLI/cron filtering (without Claude in the loop), users can pipe `--json | jq '.[] | select(.seller_name | test("VOG"))'`.

## Output

Default text format prints one row per invoice with netto/VAT/brutto, plus a totals line when there's >1 result:
```
2026-05-04  FS/1/05/2026     net    150.00  vat    34.50  gross    184.50 PLN  from 6771014090 BIURO USŁUG KSIĘGOWO-PODATKOWYCH "VOG"
    ksef: 6771014090-20260504-587951400004-57
```

`--json` emits a list of objects with: `ksef_number`, `invoice_number`, `issue_date`, `invoicing_date`, `permanent_storage_date`, `seller_nip`, `seller_name`, `buyer_id`, `buyer_name`, `net_amount`, `gross_amount`, `vat_amount`, `currency`, `invoice_type`, `has_attachment`.

## Designing automation on top of this

The `--json` mode is the integration point. A future routine that watches for new purchase invoices would:

1. Maintain a state file (e.g. `data/ksef_seen.json`) with a high-watermark `permanent_storage_date` and the set of seen `ksef_number`s.
2. On each tick, call `--role buyer --from <last_watermark> --json --date-type permanent_storage`.
3. Diff results against the seen set; report only new entries.
4. Update the watermark to `max(permanent_storage_date)` from the response.

`permanent_storage_date` is monotonically increasing as KSeF persists invoices, so it's the right watermark for an incremental sync — not `invoicing_date` (which can be backdated by sellers).

When the user asks to "set up notifications for new invoices" / "stwórz rutynę śledzącą nowe faktury", point them at the `schedule` skill (cron-like scheduling) or the `loop` skill (interval polling) and have the cron call this script with `--json --date-type permanent_storage`.

## Safety / limits

- Read-only path — uses dedicated `KSEF_READ_INVOICES_TOKEN`, never `KSEF_TOKEN` (which has write permissions).
- KSeF prod environment hardcoded inside `_build_auth(env="prod")`. Don't change to test/demo unless the user explicitly asks — the read token is paired with prod.
- Respect API: 3-month single-query cap is handled by chunking; don't bypass it.

## Language

Reply in the language the user used (PL or EN). When showing output, the table format above is fine in either language.
