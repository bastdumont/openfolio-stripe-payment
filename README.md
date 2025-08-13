# 🚀 OpenFolio Stripe Payment System

A modern, multilingual investment portfolio platform with integrated Stripe payment processing. Built with Flask backend and responsive frontend design.

![OpenFolio Banner](https://img.shields.io/badge/OpenFolio-Investment_Platform-FFB500?style=for-the-badge&logo=bitcoin&logoColor=white)

## ✨ Features

- **🌐 Multilingual Support**: French, German, and English interfaces
- **💳 Stripe Integration**: Secure subscription-based payments
- **📱 Responsive Design**: Optimized for all devices
- **🎨 Modern UI/UX**: Balder App design system with premium styling
- **💰 Investment Portfolios**:
  - ImmoFolio (Real Estate)
  - CryptoFolio (Direct Crypto)
  - IndirectCryptoFolio (Crypto Stocks/ETFs)
  - TechnoFolio (Future Technologies)

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

4. **Set up environment variables**:

   ```bash
   # Create .env file
   cp .env.example .env

   # Add your Stripe keys
   STRIPE_SECRET_KEY=sk_test_your_secret_key_here
   STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
   PORT=4242
   ```

5. **Run the development server**:

   ```bash
   python server.py
   ```

6. **Open in browser**: http://localhost:4242

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
   - `STRIPE_SECRET_KEY`: Your Stripe secret key
   - `PORT`: 4242

### Environment Variables Setup

In your Vercel dashboard:

1. Go to your project settings
2. Navigate to "Environment Variables"
3. Add the following variables:

| Variable            | Value                          | Environment |
| ------------------- | ------------------------------ | ----------- |
| `STRIPE_SECRET_KEY` | `sk_test_...` or `sk_live_...` | All         |
| `PORT`              | `4242`                         | All         |

### Vercel Runtime Notes

- The Flask app is exposed as a WSGI application via `app = create_app()` in `server.py` so Vercel can import it.
- `vercel.json` routes map `/` to `open_folio_multilingual_landing_fr_de_en_with_i_18_n.html` and `/payment` to `stripe_payment_page.html`. All other paths fall back to `server.py`.
- Make sure your Vercel project has the `STRIPE_SECRET_KEY` environment variable set; otherwise, API routes will return a configuration error.

## 📁 Project Structure

```
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

### Payment Endpoints

- `GET /` - Landing page
- `GET /payment` - Payment page
- `POST /create-subscription` - Create Stripe subscription
- `POST /cancel-subscription` - Cancel subscription
- `GET /list-subscriptions` - List customer subscriptions
- `GET /health` - Health check

### Request/Response Examples

**Create Subscription**:

```json
POST /create-subscription
{
  "email": "user@example.com",
  "name": "John Doe",
  "priceId": "price_1234567890",
  "portfolios": ["ImmoFolio", "CryptoFolio"]
}

Response:
{
  "subscriptionId": "sub_1234567890",
  "clientSecret": "pi_1234567890_secret_...",
  "customerId": "cus_1234567890"
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

Use Stripe CLI for local webhook testing:

```bash
stripe listen --forward-to localhost:4242/webhook
```

## 📊 Portfolio Pricing

| Portfolio    | 6 Months | 12 Months | Savings |
| ------------ | -------- | --------- | ------- |
| 1 Portfolio  | 180 CHF  | 324 CHF   | 10%     |
| 2 Portfolios | 324 CHF  | 583 CHF   | 20%     |
| 3 Portfolios | 432 CHF  | 778 CHF   | 30%     |
| 4 Portfolios | 504 CHF  | 907 CHF   | 40%     |

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
