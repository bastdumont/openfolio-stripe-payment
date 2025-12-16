# 🚀 OpenFolio Stripe Payment System

A modern, multilingual investment portfolio platform with integrated Stripe payment processing. Built with Flask backend and responsive frontend design.

![OpenFolio Banner](https://img.shields.io/badge/OpenFolio-Investment_Platform-FFB500?style=for-the-badge&logo=bitcoin&logoColor=white)

## ✨ Features

- **🌐 Multilingual Support**: French, German, and English interfaces
- **💳 Stripe Integration**: Secure subscription-based payments
- **🧾 VAT Handling**: Automatically adds Swiss VAT (8.1%) with HT/TTC breakdown before checkout
- **📱 Responsive Design**: Optimized for all devices
- **🎨 Modern UI/UX**: Balder App design system with premium styling
- **💰 Investment Portfolios**:
  - ImmoFolio (Real Estate)
  - CryptoFolio (Direct Crypto)
  - IndirectCryptoFolio (Crypto Stocks/ETFs)
  - TechnoFolio (Future Technologies)
- **📲 Mobile App Access**: Dedicated `openfolio-app-link.html` page with store badges and QR codes for instant installs

## 🛠️ Technology Stack

- **Backend**: Python Flask
- **Frontend**: HTML5, CSS3, JavaScript
- **Payments**: Stripe API
- **Deployment**: Vercel
- **Styling**: Custom CSS with design system

## 🚀 Quick Start

### Local Development

1. **Clone the repository**:

   ```bash
   git clone https://github.com/YOUR_USERNAME/openfolio-stripe-payment.git
   cd openfolio-stripe-payment
   ```

2. **Create virtual environment**:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables**:

   ```bash
   # Required: Stripe API key
   export STRIPE_SECRET_KEY=sk_test_your_key_here
   
   # Optional: Server port (defaults to 4242)
   export PORT=4242
   
   # Required for profile form email notifications:
   export SMTP_HOST=mail.balder-app.com
   export SMTP_PORT=587
   export SMTP_USER=openfolio@balder-app.com
   export SMTP_PASSWORD=your_smtp_password_here
   export PROFILE_NOTIFICATION_EMAIL=bastien@balder-app.com
   ```

4. **Set up environment variables**:

   ```bash
   # Create .env file (optional, for local development)
   cp env.example .env

   # Add your Stripe secret key (required for backend)
   # Replace 'sk_test_your_secret_key_here' with your actual Stripe secret key
   export STRIPE_SECRET_KEY=sk_test_your_secret_key_here
   export PORT=4242  # optional, defaults to 4242

   # Note: STRIPE_PUBLISHABLE_KEY is hardcoded in stripe_payment_page.html
   # Update it directly in the HTML file (line ~1484)
   ```

5. **Run the development server**:

   ```bash
   python server.py
   ```

6. **Open in browser**: http://localhost:4242

## 📲 Mobile App Download Page

- **Path**: `openfolio-app-link.html` (served at `/app-link` when running the Flask server)
- **What it includes**: Branded OpenFolio hero, Google Play / App Store buttons, and QR codes that deep-link to the official listings
- **How to use locally**: Start the Flask server and visit http://localhost:4242/app-link to access the install handoff page
- **Deployment note**: The page is static, so it deploys automatically with the rest of the project and stays in sync across environments

## 🌐 Vercel Deployment

### One-Click Deploy

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/YOUR_USERNAME/openfolio-stripe-payment)

### Manual Deployment

1. **Install Vercel CLI**:

   ```bash
   npm i -g vercel
   ```

2. **Login to Vercel**:

   ```bash
   vercel login
   ```

3. **Deploy**:

   ```bash
   vercel --prod
   ```

4. **Set Environment Variables** in Vercel Dashboard:
   - `STRIPE_SECRET_KEY`: Your Stripe secret key (required)
   - `PORT`: 4242 (optional)

   **Important**: The `STRIPE_PUBLISHABLE_KEY` is hardcoded in `stripe_payment_page.html` (around line 1484). Update it directly in the HTML file before deploying.

### Environment Variables Setup

In your Vercel dashboard:

1. Go to your project settings
2. Navigate to "Environment Variables"
3. Add the following variables:

| Variable            | Value                          | Environment | Notes                                    |
| ------------------- | ------------------------------ | ----------- | ---------------------------------------- |
| `STRIPE_SECRET_KEY` | `sk_test_...` or `sk_live_...` | All         | Required for backend API                 |
| `PORT`              | `4242`                         | All         | Optional, defaults to 4242               |
| `STRIPE_PUBLISHABLE_KEY` | `pk_test_...` or `pk_live_...` | N/A         | Hardcoded in `stripe_payment_page.html` |

### Vercel Runtime Notes

- The Flask app is exposed as a WSGI application via `app = create_app()` in `server.py` so Vercel can import it.
- `vercel.json` routes map `/` to `open_folio_multilingual_landing_fr_de_en_with_i_18_n.html` and `/payment` to `stripe_payment_page.html`. All other paths fall back to `server.py`.
- Make sure your Vercel project has the `STRIPE_SECRET_KEY` environment variable set; otherwise, API routes will return a configuration error.

## 📁 Project Structure

```text
openfolio-stripe-payment/
├── server.py                                    # Flask backend
├── open_folio_multilingual_landing_*.html       # Landing page
├── stripe_payment_page.html                     # Payment interface
├── requirements.txt                             # Python dependencies
├── package.json                                 # Node.js metadata
├── vercel.json                                  # Vercel configuration
├── .env.example                                 # Environment template
├── .gitignore                                   # Git ignore rules
└── README.md                                    # This file
```

## 🔧 API Endpoints

### Page Routes

- `GET /` - Landing page (multilingual)
- `GET /payment` - Payment page with Stripe Checkout
- `GET /privacy` - Privacy policy page
- `GET /terms` - Terms and conditions page

### API Endpoints

- `GET /health` - Health check (returns Stripe configuration status)
- `POST /create-checkout-session` - Create Stripe Checkout Session (primary payment flow)
- `POST /create-subscription-incomplete` - Create subscription with incomplete status (for wallet payments)
- `POST /verify-subscription` - Verify subscription payment status
- `POST /cancel-subscription` - Cancel a subscription
- `GET /list-subscriptions` - List customer subscriptions (optional email query param)

### Request/Response Examples

**Create Checkout Session** (Primary Payment Flow):

```json
POST /create-checkout-session
{
  "email": "user@example.com",
  "name": "John Doe",
  "portfolioCount": 2,
  "billingPeriod": "annual",
  "portfolios": ["ImmoFolio", "CryptoFolio"]
}

Response:
{
  "url": "https://checkout.stripe.com/c/pay/...",
  "sessionId": "cs_test_..."
}
```

**Create Subscription (Incomplete)** - For wallet payments:

```json
POST /create-subscription-incomplete
{
  "email": "user@example.com",
  "name": "John Doe",
  "portfolioCount": 2,
  "billingPeriod": "biannual",
  "portfolios": ["ImmoFolio", "CryptoFolio"]
}

Response:
{
  "subscriptionId": "sub_1234567890",
  "clientSecret": "pi_1234567890_secret_...",
  "customerId": "cus_1234567890",
  "priceId": "price_1234567890",
  "paymentIntentId": "pi_1234567890"
}
```

## 🎨 Design System

The application uses the **Balder App** design system:

- **Primary Color**: `#FFB500` (Energy Yellow)
- **Typography**: Heebo font family
- **Spacing**: 32-level spacing scale
- **Shadows**: 6-level shadow hierarchy
- **Responsive**: Mobile-first approach
- **Accessibility**: WCAG AA compliant

## 🔒 Security

- **Stripe Integration**: PCI-compliant payment processing
- **Environment Variables**: Secure API key management
- **CORS Protection**: Configured for production
- **Input Validation**: Server-side validation
- **HTTPS**: Force HTTPS in production

## 🧪 Testing

### Test Cards (Stripe Test Mode)

| Card Number        | Brand      | Description        |
| ------------------ | ---------- | ------------------ |
| `4242424242424242` | Visa       | Successful payment |
| `5555555555554444` | Mastercard | Successful payment |
| `4000000000000002` | Visa       | Declined payment   |

### Test Webhooks

**Note**: This application uses Stripe Checkout Sessions which handle webhooks automatically. No custom webhook endpoint is required for basic subscription functionality.

If you need to add custom webhook handling, create a `/webhook` endpoint and use:

```bash
stripe listen --forward-to localhost:4242/webhook
```

## 📊 Portfolio Pricing

| Portfolio Count | 6 Months (HT) | 12 Months (HT) | Volume Discount | Annual Savings |
| --------------- | -------- | --------- | --------------- | -------------- |
| 1 Portfolio     | 180 CHF  | 324 CHF   | 0%              | 10%            |
| 2 Portfolios    | 324 CHF  | 583 CHF   | 10%             | 20%            |
| 3 Portfolios    | 432 CHF  | 778 CHF   | 20%             | 30%            |
| 4 Portfolios    | 504 CHF  | 907 CHF   | 30%             | 40%            |

**Pricing Logic**:

- Base price: 180 CHF per portfolio for 6 months (HT)
- Volume discounts: 0%, 10%, 20%, 30% for 1-4 portfolios
- Annual billing: Additional 10% discount on top of volume discount
- Swiss VAT: 8.1% VAT is applied on top of the discounted amount and surfaced on the payment page before redirecting to Stripe Checkout

> Final TTC amounts (HT + 8.1% VAT) are displayed on the payment page before redirecting to Stripe Checkout.

## 🚀 Performance

- **Loading Time**: < 2s first paint
- **Mobile Score**: 95+ Lighthouse
- **SEO Optimized**: Meta tags and structured data
- **Responsive**: All device sizes supported

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- **Documentation**: [GitHub Wiki](https://github.com/YOUR_USERNAME/openfolio-stripe-payment/wiki)
- **Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/openfolio-stripe-payment/issues)
- **Email**: support@openfolio.com

## 🔗 Links

- **Live Demo**: [https://openfolio-stripe-payment.vercel.app](https://openfolio-stripe-payment.vercel.app)
- **Stripe Dashboard**: [https://dashboard.stripe.com](https://dashboard.stripe.com)
- **Vercel Dashboard**: [https://vercel.com/dashboard](https://vercel.com/dashboard)

---

**Made with ❤️ by the OpenFolio Team**

![Footer](https://img.shields.io/badge/Powered_by-Stripe_+_Vercel-blue?style=flat-square)
