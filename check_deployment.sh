#!/bin/bash
echo "🔍 Checking Vercel Deployment Status..."
echo ""

# Check if project is linked
if [ -f .vercel/project.json ]; then
    PROJECT_NAME=$(cat .vercel/project.json | grep -o '"projectName":"[^"]*"' | cut -d'"' -f4)
    echo "✅ Project Linked: $PROJECT_NAME"
else
    echo "❌ Project not linked. Run: vercel link"
    exit 1
fi

# Check deployments
echo ""
echo "📦 Recent Deployments:"
DEPLOYMENTS=$(vercel ls --yes 2>&1 | grep -E "(openfolio|https://)" | head -5)
if [ -z "$DEPLOYMENTS" ] || echo "$DEPLOYMENTS" | grep -q "No deployments"; then
    echo "⚠️  No deployments found yet"
    echo ""
    echo "To deploy, run:"
    echo "  1. Set STRIPE_SECRET_KEY in Vercel dashboard"
    echo "  2. Run: vercel --prod"
else
    echo "$DEPLOYMENTS"
fi

# Check environment variables
echo ""
echo "🔑 Environment Variables:"
ENV_VARS=$(vercel env ls 2>&1)
if echo "$ENV_VARS" | grep -q "No Environment Variables"; then
    echo "⚠️  STRIPE_SECRET_KEY not set"
    echo "   Set it at: https://vercel.com/bastdumonts-projects/openfolio-stripe-payment/settings/environment-variables"
else
    echo "$ENV_VARS"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
