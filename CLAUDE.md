# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

OpenFolio is a multilingual investment portfolio subscription platform with Stripe payment integration. The application allows users to subscribe to investment portfolios (ImmoFolio, CryptoFolio, IndirectCryptoFolio, TechnoFolio) with subscription-based payments in Swiss Francs (CHF).

**Tech Stack**: Flask (Python), Stripe API, Vercel serverless deployment, vanilla HTML/CSS/JavaScript frontend

## Development Commands

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set required environment variables
export STRIPE_SECRET_KEY=sk_test_your_key_here
export PORT=4242  # optional, defaults to 4242

# Run development server
python server.py

# Access application
open http://localhost:4242
```

### Testing with Stripe

Use Stripe test mode cards:
- Success: `4242424242424242`
- Decline: `4000000000000002`

No build or lint commands exist - this is a straightforward Python/Flask app without a complex build process.

## Architecture

### Backend: Flask Application ([server.py](server.py))

The Flask app uses a factory pattern (`create_app()`) that returns a WSGI-compatible app for Vercel serverless deployment. The module-level `app = create_app()` export is required for Vercel's `@vercel/python` runtime.

**Key architectural decisions:**

1. **Dynamic Stripe Price Generation**: The `get_or_create_price()` function (lines 102-182) dynamically creates or retrieves Stripe prices based on:
   - Portfolio count (1-4)
   - Billing period ('biannual' or 'annual')
   - Volume discounts (10%, 20%, 30% for 2, 3, 4 portfolios)
   - Annual discount (additional 10% for annual billing)

   Prices are looked up by `lookup_key` to avoid duplicate creation. If not found, a new recurring price is created with appropriate metadata.

2. **Stripe Checkout Payment Flow**: The app uses Stripe Checkout Sessions for a streamlined payment experience:
   - `/create-checkout-session` endpoint (lines 617-767) creates a Checkout Session with the dynamically generated price
   - User is redirected to Stripe's hosted payment page (invoice view)
   - Upon successful payment, Stripe automatically activates the subscription
   - User is redirected back to `/payment?session_id=xxx&success=true`
   - Frontend displays success message based on URL parameters

   This approach provides:
   - Professional hosted invoice page
   - Automatic subscription activation
   - Built-in payment method storage
   - Support for multiple payment methods (cards, Apple Pay, Google Pay, etc.)
   - No need for Stripe Elements integration on frontend

3. **Error Handling**: Custom error handlers (lines 49-75) ensure API endpoints always return JSON, never HTML error pages. This is critical for the JavaScript frontend error handling.

4. **Customer Management**: The app reuses existing Stripe customers by email lookup (line 305) to maintain customer history and payment methods.

### Frontend: Static HTML Pages

- **Landing page**: `open_folio_multilingual_landing_fr_de_en_with_i_18_n.html` - Multilingual (FR/DE/EN) landing with i18n
- **Payment page**: `stripe_payment_page.html` - Complete Stripe Elements integration with portfolio selection UI
- **Legal pages**: `privacy.html`, `cg.html` (Conditions Générales/Terms)

The payment page contains:
- Balder App design system with CSS custom properties (lines 22-100 in HTML)
- Portfolio selection logic with dynamic pricing calculations matching backend
- Stripe Checkout integration - redirects to hosted payment page
- Success/cancel redirect handlers (lines 1991-2015) that display appropriate messages
- Three-step flow: Portfolio selection → Customer info → Redirect to Stripe Checkout

### Routing: Vercel Configuration ([vercel.json](vercel.json))

Static routes map directly to HTML files:
- `/` → landing page
- `/payment` → payment page
- `/privacy`, `/terms` → legal pages

All API routes (health check, subscription creation/verification/cancellation) fall through to `server.py`.

## Critical Implementation Details

### Stripe Publishable Key Location

The Stripe publishable key is **hardcoded in the HTML** at [stripe_payment_page.html:1484-1485](stripe_payment_page.html#L1484-L1485). When switching between test/live modes or deploying to new environments, update this constant:

```javascript
const STRIPE_PUBLISHABLE_KEY = 'pk_test_...'; // or pk_live_...
```

The backend Stripe secret key comes from the `STRIPE_SECRET_KEY` environment variable ([server.py:12](server.py#L12)).

### Base Product ID

The Stripe product ID is hardcoded at [server.py:252](server.py#L252):
```python
base_product_id = "prod_TMSfbpU4NW2fRK"
```

All dynamically created prices attach to this product. If creating a new Stripe account or product, update this ID.

### Pricing Logic Consistency

Pricing calculations exist in **both frontend and backend** and must stay synchronized:
- Backend: `get_or_create_price()` function ([server.py:102-182](server.py#L102-L182))
- Frontend: JavaScript price calculation in payment page (around line 1500+)

Base price: 180 CHF per portfolio for 6 months
Volume discounts: 0%, 10%, 20%, 30% for 1-4 portfolios
Annual discount: Additional 10% off for annual billing

### Environment Variables

Required for operation:
- `STRIPE_SECRET_KEY` (required): Backend Stripe API authentication
- `PORT` (optional, default 4242): Local development server port

The app validates Stripe key presence and provides helpful error messages if missing ([server.py:633-643](server.py#L633-L643)).

## Common Development Scenarios

### Adding a New API Endpoint

1. Add route handler in [server.py](server.py) within the `create_app()` function
2. Add route mapping in [vercel.json](vercel.json) routes array
3. Ensure JSON error handling by adding path to `after_request` filter ([server.py:23-27](server.py#L23-L27))

### Modifying Pricing Structure

1. Update discount logic in `get_or_create_price()` ([server.py:113-132](server.py#L113-L132))
2. Update frontend price calculation in payment page JavaScript
3. Consider clearing old prices in Stripe dashboard or implementing price versioning

### Adding a New Portfolio

1. Update portfolio list in landing page HTML
2. Update metadata handling in subscription creation endpoint
3. No backend logic changes needed - portfolio count drives pricing, not names

### Deploying to Vercel

The repository is configured for Vercel deployment via [vercel.json](vercel.json).

**Critical deployment files:**
- [vercel.json](vercel.json): Routes all requests to `server.py` (Flask handles routing internally)
- [runtime.txt](runtime.txt): Specifies Python 3.9 (Vercel's supported version)
- [requirements.txt](requirements.txt): Python dependencies
- `.vercelignore`: Excludes local files from deployment

**Required environment variables in Vercel dashboard:**
- `STRIPE_SECRET_KEY`: Your Stripe secret key (test or live)

The Flask app uses the factory pattern with module-level export (`app = create_app()`) which Vercel's `@vercel/python` runtime imports automatically.

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for complete deployment instructions.

## Debugging Tips

- **Check Stripe mode**: The payment page detects test vs. live mode by checking if publishable key starts with `pk_test_` (line 2120 in HTML)
- **Backend logs**: In local development, Flask prints detailed logs. On Vercel, check function logs in dashboard
- **Stripe Dashboard**: Use Stripe dashboard logs to trace API calls and payment events
- **Health check**: Hit `/health` endpoint to verify Stripe configuration: returns `{"status": "ok", "stripe_configured": true/false}`

## Important File Relationships

- [vercel.json](vercel.json) routes determine which requests go to static files vs. [server.py](server.py)
- [server.py](server.py) dynamic price creation must match frontend calculations in [stripe_payment_page.html](stripe_payment_page.html)
- Portfolio metadata passed from frontend to backend is stored but not validated - frontend controls portfolio selection logic
- The `create_app()` factory pattern in [server.py](server.py) is required for Vercel's Python runtime to import the WSGI app
