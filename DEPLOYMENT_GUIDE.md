# 🚀 Deployment Guide: GitHub → Vercel

## 📋 Pre-Deployment Checklist

✅ **Project Structure Ready**
- [x] Git repository initialized
- [x] `.gitignore` configured
- [x] `vercel.json` deployment config
- [x] `package.json` metadata
- [x] `requirements.txt` dependencies
- [x] Environment template (`env.example`)
- [x] Comprehensive README.md

## 🐙 Step 1: GitHub Repository Setup

### Option A: Create New Repository on GitHub

1. **Go to GitHub**: https://github.com/new
2. **Repository Details**:
   - **Name**: `openfolio-stripe-payment`
   - **Description**: `Modern investment portfolio platform with Stripe payments`
   - **Visibility**: Public or Private (your choice)
   - ❌ **Don't initialize** with README, .gitignore, or license (we have them)

3. **Copy the repository URL** (you'll need it below)

### Option B: Use GitHub CLI (if installed)

```bash
# Create repository directly from terminal
gh repo create openfolio-stripe-payment --public --description "Modern investment portfolio platform with Stripe payments"
```

## 🔗 Step 2: Connect Local Repository to GitHub

Run these commands in your terminal:

```bash
# Add the remote repository
git remote add origin https://github.com/YOUR_USERNAME/openfolio-stripe-payment.git

# Push to GitHub
git push -u origin main
```

**Replace `YOUR_USERNAME`** with your actual GitHub username!

## 🌐 Step 3: Deploy to Vercel

### Option A: One-Click Deploy (Recommended)

1. **Go to Vercel**: https://vercel.com/new
2. **Import Git Repository**:
   - Select your GitHub account
   - Choose `openfolio-stripe-payment` repository
   - Click **Import**

3. **Configure Project**:
   - **Framework Preset**: Other
   - **Build Command**: Leave empty
   - **Output Directory**: Leave empty
   - **Install Command**: `pip install -r requirements.txt`

### Option B: Vercel CLI

```bash
# Install Vercel CLI (if not installed)
npm i -g vercel

# Login to Vercel
vercel login

# Deploy
vercel --prod
```

## 🔧 Step 4: Environment Variables Setup

In your **Vercel Dashboard**:

1. Go to your project → **Settings** → **Environment Variables**
2. Add these variables:

| Variable Name | Value | Environment |
|---------------|-------|-------------|
| `STRIPE_SECRET_KEY` | `sk_test_...` (your actual Stripe secret key) | Production, Preview, Development |
| `PORT` | `4242` | All Environments |

### Get Your Stripe Keys:

1. **Go to Stripe Dashboard**: https://dashboard.stripe.com/test/apikeys
2. **Copy Secret Key**: Starts with `sk_test_...`
3. **Copy Publishable Key**: Starts with `pk_test_...`

## 🧪 Step 5: Test Deployment

1. **Visit Your Vercel URL**: `https://your-project-name.vercel.app`
2. **Test Landing Page**: Should load the multilingual OpenFolio page
3. **Test Payment Flow**:
   - Click "Commencer aujourd'hui"
   - Select portfolios
   - Use test card: `4242424242424242`

## 🎯 Post-Deployment Steps

### 1. Update Stripe Publishable Key

Edit `stripe_payment_page.html` line ~1370:
```javascript
const STRIPE_PUBLISHABLE_KEY = 'pk_test_YOUR_ACTUAL_PUBLISHABLE_KEY_HERE';
```

### 2. Set Up Stripe Webhooks (Optional)

1. **Stripe Dashboard** → **Webhooks** → **Add endpoint**
2. **URL**: `https://your-project-name.vercel.app/webhook`
3. **Events**: `payment_intent.succeeded`, `invoice.payment_succeeded`

### 3. Custom Domain (Optional)

In **Vercel Dashboard** → **Domains**:
- Add your custom domain
- Configure DNS settings

## 🔧 Troubleshooting

### Common Issues:

**❌ Build Failed - Python Version**
- Vercel uses Python 3.9 by default
- Add `runtime.txt` with: `python-3.11.0` (if needed)

**❌ Stripe Keys Not Working**
- Check environment variables are set correctly
- Ensure you're using test keys (start with `sk_test_`)
- Verify keys are copied without extra spaces

**❌ 404 Errors**
- Check `vercel.json` routes configuration
- Ensure Flask app is running correctly

**❌ CORS Errors**
- Check Flask-CORS configuration in `server.py`
- Verify origins are allowed

### Getting Help:

1. **Vercel Logs**: Check function logs in Vercel dashboard
2. **Stripe Logs**: Check webhook and API logs in Stripe dashboard
3. **GitHub Issues**: Create an issue in your repository

## 🎉 Success Checklist

- [ ] Repository pushed to GitHub
- [ ] Vercel deployment successful
- [ ] Environment variables configured
- [ ] Landing page loads correctly
- [ ] Payment page accessible via `/payment`
- [ ] Test payment completes successfully
- [ ] Stripe webhooks working (if configured)

## 📋 Next Steps

1. **Production Setup**:
   - Switch to live Stripe keys
   - Set up production webhook endpoints
   - Configure custom domain

2. **Monitoring**:
   - Set up Vercel Analytics
   - Configure Stripe monitoring
   - Add error tracking (Sentry)

3. **Optimization**:
   - Enable Vercel Edge Functions
   - Set up CDN for static assets
   - Implement caching strategies

---

**🎯 Your project is now ready for the world!** 

Live URL: `https://your-project-name.vercel.app`
