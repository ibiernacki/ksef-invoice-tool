# KSeF setup

## Environments

| Environment | API URL | QR URL | Auth |
|---|---|---|---|
| Test | api-test.ksef.mf.gov.pl | qr-test.ksef.mf.gov.pl | Self-signed cert (auto) |
| Demo | api-demo.ksef.mf.gov.pl | qr-demo.ksef.mf.gov.pl | Self-signed cert (auto) |
| Production | api.ksef.mf.gov.pl | qr.ksef.mf.gov.pl | KSeF token from portal |

All environments use KSeF API v2 (`/v2` endpoints).

## Test environment

The test environment requires no manual setup. The tool automatically:
1. Generates a self-signed certificate
2. Creates a test subject
3. Authenticates via XAdES
4. Opens a session and submits

```bash
uv run invoice submit 2026-04 --env test
```

**Note:** Test environment uses synthetic data. Your real NIP is not exposed.

## Production token

### Step 1: Log in to KSeF portal

Go to **https://ksef.mf.gov.pl/** and log in via:
- Profil Zaufany (Trusted Profile)
- e-Dowód (electronic ID)
- Qualified electronic signature

### Step 2: Generate token

1. Navigate to **"Tokeny"** / **"Certyfikaty i Uprawnienia"**
2. Click **"Generuj nowy token"**
3. Sign the authorization request (required)
4. Copy the token — **it's displayed only once**

### Step 3: Save token

```bash
echo "KSEF_TOKEN=your-token-here" > .env
```

The `.env` file is in `.gitignore` — it's never committed.

### Step 4: Submit

```bash
uv run invoice submit 2026-04 --env prod
```

Production submission requires interactive confirmation.

## Token expiry

KSeF tokens will be **phased out on November 16, 2026**. After that date, XAdES certificate authentication (qualified signature) will be required. The tool's architecture supports both methods via the `ksef2` library.

## QR code verification

After submission, the PDF is regenerated with a QR code containing:
- Seller NIP
- Invoice date (DD-MM-YYYY)
- SHA-256 hash of the XML (Base64URL)

Scanning the QR leads to `https://qr.ksef.mf.gov.pl/invoice/...` where anyone can verify the invoice exists in KSeF — no login required.
