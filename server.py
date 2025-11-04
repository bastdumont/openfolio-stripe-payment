import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import stripe


def create_app() -> Flask:
    app = Flask(__name__, static_folder='.')
    CORS(app)

    # Configure Stripe using environment variable for security
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

    # Configure Flask to not show detailed error pages
    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.config['DEBUG'] = False  # Disable debug mode in production
    
    # Ensure API endpoints always return JSON
    @app.after_request
    def after_request(response):
        """Ensure error responses are JSON for API endpoints."""
        # Only modify responses for API routes
        if request.path.startswith('/create-subscription') or \
           request.path.startswith('/cancel-subscription') or \
           request.path.startswith('/list-subscriptions'):
            # If response is an error and not already JSON, convert it
            if response.status_code >= 400 and 'application/json' not in response.content_type:
                try:
                    # Try to parse as JSON first
                    import json
                    data = response.get_data(as_text=True)
                    # If it's HTML, replace with JSON error
                    if data and ('<html>' in data.lower() or '<!doctype' in data.lower()):
                        return jsonify({
                            "error": {
                                "message": "Internal server error. Please try again later.",
                                "type": "server_error"
                            }
                        }), response.status_code
                except:
                    pass
            # Always set Content-Type to JSON for API endpoints
            response.headers['Content-Type'] = 'application/json'
        return response
    
    # Global error handler to ensure all errors return JSON
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors and return JSON instead of HTML."""
        import traceback
        error_trace = traceback.format_exc()
        app.logger.error(f"Internal server error: {str(error)}\n{error_trace}")
        return jsonify({
            "error": {
                "message": "Internal server error. Please try again later.",
                "type": "server_error"
            }
        }), 500

    # Register error handler for all exceptions at the Flask level
    @app.errorhandler(Exception)
    def handle_exception(e):
        """Handle any unhandled exceptions and return JSON."""
        import traceback
        error_trace = traceback.format_exc()
        app.logger.error(f"Unhandled exception: {str(e)}\n{error_trace}")
        # Make sure we return JSON, never HTML
        return jsonify({
            "error": {
                "message": f"An error occurred: {str(e)}",
                "type": "unhandled_error"
            }
        }), 500

    @app.route('/')
    def index():
        """Serve the OpenFolio landing page as home page."""
        return send_from_directory('.', 'open_folio_multilingual_landing_fr_de_en_with_i_18_n.html')
    
    @app.route('/payment')
    def payment():
        """Serve the Stripe payment page."""
        return send_from_directory('.', 'stripe_payment_page.html')

    @app.route('/privacy')
    def privacy():
        """Serve the privacy policy page."""
        return send_from_directory('.', 'privacy.html')

    @app.route('/terms')
    def terms():
        """Serve the general conditions page."""
        return send_from_directory('.', 'cg.html')

    @app.route("/health", methods=["GET"])
    def health():
        """Basic health check endpoint."""
        return jsonify({"status": "ok", "stripe_configured": bool(stripe.api_key)}), 200

    def get_or_create_price(portfolio_count, billing_period, base_product_id):
        """Get or create a Stripe price with the correct discount based on portfolio count and billing period.
        
        Args:
            portfolio_count: Number of portfolios (1-4)
            billing_period: 'biannual' or 'annual'
            base_product_id: The base product ID to use
            
        Returns:
            Stripe Price object
        """
        # Discount configuration (matches frontend)
        base_price = 180.0  # CHF per portfolio for 6 months
        volume_discounts = {
            1: 0.0,    # 0% discount
            2: 0.1,    # 10% discount
            3: 0.2,    # 20% discount
            4: 0.3,    # 30% discount
        }
        annual_discount = 0.1  # 10% additional discount for annual
        
        # Calculate discounted price
        original_total = base_price * portfolio_count * (2 if billing_period == 'annual' else 1)
        volume_discount = volume_discounts.get(portfolio_count, 0)
        discounted_total = original_total * (1 - volume_discount)
        
        if billing_period == 'annual':
            discounted_total *= (1 - annual_discount)
        
        # Round to 2 decimal places and convert to cents
        amount_cents = int(round(discounted_total * 100))
        
        # Create lookup key for price identification
        lookup_key = f"openfolio_{billing_period}_{portfolio_count}_portfolios"
        
        # Try to find existing price with this lookup key
        try:
            prices = stripe.Price.list(
                lookup_keys=[lookup_key],
                active=True,
                limit=1
            )
            if prices.data:
                return prices.data[0]
        except Exception as e:
            app.logger.warning(f"Error searching for existing price: {str(e)}")
        
        # Price doesn't exist, create it
        try:
            # Determine interval based on billing period
            if billing_period == 'annual':
                interval = 'year'
                interval_count = 1
            else:  # biannual
                interval = 'month'
                interval_count = 6
            
            price = stripe.Price.create(
                product=base_product_id,
                unit_amount=amount_cents,
                currency='chf',
                recurring={
                    'interval': interval,
                    'interval_count': interval_count,
                },
                lookup_key=lookup_key,
                metadata={
                    'portfolio_count': str(portfolio_count),
                    'billing_period': billing_period,
                    'original_amount': str(original_total),
                    'discounted_amount': str(discounted_total),
                    'volume_discount': str(volume_discount),
                    'annual_discount_applied': str(billing_period == 'annual')
                },
                nickname=f"OpenFolio {billing_period.capitalize()} - {portfolio_count} portfolio{'s' if portfolio_count > 1 else ''}"
            )
            app.logger.info(f"Created new price {price.id} for {portfolio_count} portfolios, {billing_period} billing, amount: {discounted_total} CHF")
            return price
        except Exception as e:
            app.logger.error(f"Error creating price: {str(e)}")
            raise

    @app.route("/create-payment-intent", methods=["POST"])
    def create_payment_intent():
        """Create a PaymentIntent for the selected price. Subscription will be created after payment succeeds.

        Expected JSON body:
        - email: Customer email
        - name: Customer full name
        - priceId: Stripe Price ID (recurring) OR portfolioCount and billingPeriod to create price dynamically
        - portfolios: List of selected portfolio names (optional, for metadata)
        - portfolioCount: Number of portfolios (1-4) - used if priceId not provided
        - billingPeriod: 'biannual' or 'annual' - used if priceId not provided
        
        Returns:
        - clientSecret: PaymentIntent client secret for frontend confirmation
        - customerId: Customer ID (created or existing)
        - priceId: The price ID used
        """
        if not stripe.api_key:
            return jsonify({
                "error": {
                    "message": "Server not configured. Set STRIPE_SECRET_KEY environment variable."
                }
            }), 500

        # Get JSON data from request with proper error handling
        try:
            data = request.get_json(force=False, silent=True)
            if data is None:
                if request.is_json:
                    data = {}
                else:
                    return jsonify({
                        "error": {
                            "message": "Invalid request. JSON body required."
                        }
                    }), 400
        except Exception as e:
            app.logger.error(f"Error parsing JSON request: {str(e)}")
            return jsonify({
                "error": {
                    "message": f"Error parsing request: {str(e)}"
                }
            }), 400
        
        email = data.get("email") if data else None
        name = data.get("name") if data else None
        price_id = data.get("priceId") if data else None
        portfolios = data.get("portfolios", []) if data else []
        portfolio_count = data.get("portfolioCount", len(portfolios) if portfolios else 1)
        billing_period = data.get("billingPeriod", 'biannual')

        if not email or not name:
            return jsonify({
                "error": {
                    "message": "Missing required fields: email, name"
                }
            }), 400

        try:
            # Get base product ID (use the existing product)
            base_product_id = "prod_TMSfbpU4NW2fRK"  # The main Portfolio Subscription product
            
            # If priceId is provided, validate it; otherwise create/get price based on portfolio count and billing
            if price_id:
                try:
                    price = stripe.Price.retrieve(price_id)
                    if not price.active:
                        return jsonify({
                            "error": {
                                "message": f"Price {price_id} is not active. Please contact support."
                            }
                        }), 400
                    if price.type != "recurring":
                        return jsonify({
                            "error": {
                                "message": f"Price {price_id} is not a recurring price. Subscriptions require recurring prices."
                            }
                        }), 400
                except stripe.error.InvalidRequestError as e:
                    app.logger.error(f"Price retrieval failed: {str(e)}")
                    is_test_key = stripe.api_key.startswith('sk_test_')
                    is_live_price = price_id.startswith('price_1') and len(price_id) > 20
                    error_msg = f"Price ID {price_id} not found or not accessible."
                    if is_test_key and is_live_price:
                        error_msg += " You're using a TEST API key but a LIVE price ID. Use test price IDs or switch to live API key."
                    elif not is_test_key and not is_live_price:
                        error_msg += " You're using a LIVE API key but possibly a test price ID. Use live price IDs."
                    return jsonify({
                        "error": {
                            "message": error_msg,
                            "type": "invalid_request_error"
                        }
                    }), 400
            else:
                # Create or get price based on portfolio count and billing period
                if portfolio_count < 1 or portfolio_count > 4:
                    return jsonify({
                        "error": {
                            "message": "Portfolio count must be between 1 and 4"
                        }
                    }), 400
                
                if billing_period not in ['biannual', 'annual']:
                    return jsonify({
                        "error": {
                            "message": "Billing period must be 'biannual' or 'annual'"
                        }
                    }), 400
                
                price = get_or_create_price(portfolio_count, billing_period, base_product_id)
                price_id = price.id
            
            # Check if a customer with this email already exists
            existing_customers = stripe.Customer.list(email=email, limit=1)
            
            if existing_customers.data:
                customer = existing_customers.data[0]
                # Update the customer's name if it has changed
                if customer.name != name:
                    customer = stripe.Customer.modify(customer.id, name=name)
            else:
                # Create a new customer with metadata
                customer = stripe.Customer.create(
                    email=email, 
                    name=name,
                    metadata={
                        "selected_portfolios": ", ".join(portfolios) if portfolios else "N/A"
                    }
                )

            # Create a PaymentIntent for the subscription amount
            # This will be used to collect payment, then we'll create the subscription
            payment_intent = stripe.PaymentIntent.create(
                amount=price.unit_amount,  # Amount in cents
                currency=price.currency,
                customer=customer.id,
                payment_method_types=["card"],  # Only card payments
                metadata={
                    "price_id": price_id,
                    "portfolios": ", ".join(portfolios) if portfolios else "N/A",
                    "portfolio_count": str(len(portfolios)),
                    "subscription_pending": "true"  # Flag to indicate subscription will be created after payment
                },
                description=f"OpenFolio Subscription - {', '.join(portfolios) if portfolios else 'All portfolios'}"
            )

            return jsonify({
                "clientSecret": payment_intent.client_secret,
                "customerId": customer.id,
                "priceId": price_id,
                "paymentIntentId": payment_intent.id
            })

        except stripe.error.CardError as e:
            return jsonify({
                "error": {
                    "type": "card_error",
                    "message": e.user_message or "Your card was declined.",
                }
            }), 400
        except stripe.error.RateLimitError as e:
            return jsonify({
                "error": {
                    "type": "rate_limit_error",
                    "message": "Too many requests. Please try again later.",
                }
            }), 429
        except stripe.error.InvalidRequestError as e:
            return jsonify({
                "error": {
                    "type": "invalid_request_error",
                    "message": str(e),
                }
            }), 400
        except stripe.error.AuthenticationError as e:
            return jsonify({
                "error": {
                    "type": "authentication_error",
                    "message": "Authentication with payment provider failed.",
                }
            }), 401
        except stripe.error.APIConnectionError as e:
            return jsonify({
                "error": {
                    "type": "api_connection_error",
                    "message": "Network error. Please try again.",
                }
            }), 502
        except stripe.error.StripeError as e:
            return jsonify({
                "error": {
                    "type": "stripe_error",
                    "message": e.user_message or str(e),
                }
            }), 400
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            app.logger.error(f"Unexpected error in create_payment_intent: {str(e)}\n{error_trace}")
            return jsonify({
                "error": {
                    "message": f"Server error: {str(e)}",
                    "type": "server_error"
                }
            }), 500

    @app.route("/create-subscription", methods=["POST"])
    def create_subscription():
        """Create a Stripe Subscription after payment has succeeded.
        
        Expected JSON body:
        - customerId: Customer ID
        - priceId: Stripe Price ID (recurring)
        - paymentIntentId: PaymentIntent ID that was successfully paid
        - portfolios: List of selected portfolio names (optional, for metadata)
        
        Returns:
        - subscriptionId: Created subscription ID
        """
        if not stripe.api_key:
            return jsonify({
                "error": {
                    "message": "Server not configured. Set STRIPE_SECRET_KEY environment variable."
                }
            }), 500

        # Get JSON data from request
        try:
            data = request.get_json(force=False, silent=True)
            if data is None:
                if request.is_json:
                    data = {}
                else:
                    return jsonify({
                        "error": {
                            "message": "Invalid request. JSON body required."
                        }
                    }), 400
        except Exception as e:
            app.logger.error(f"Error parsing JSON request: {str(e)}")
            return jsonify({
                "error": {
                    "message": f"Error parsing request: {str(e)}"
                }
            }), 400
        
        customer_id = data.get("customerId") if data else None
        price_id = data.get("priceId") if data else None
        payment_intent_id = data.get("paymentIntentId") if data else None
        portfolios = data.get("portfolios", []) if data else []

        if not customer_id or not price_id or not payment_intent_id:
            return jsonify({
                "error": {
                    "message": "Missing required fields: customerId, priceId, paymentIntentId"
                }
            }), 400

        try:
            # Verify the PaymentIntent was successful
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            if payment_intent.status != "succeeded":
                return jsonify({
                    "error": {
                        "message": f"PaymentIntent {payment_intent_id} has not succeeded. Status: {payment_intent.status}"
                    }
                }), 400
            
            # Verify the customer exists
            customer = stripe.Customer.retrieve(customer_id)
            
            # Get the payment method from the PaymentIntent
            payment_method_id = payment_intent.payment_method
            
            if not payment_method_id:
                return jsonify({
                    "error": {
                        "message": "PaymentIntent does not have a payment method attached."
                    }
                }), 400
            
            # Step 1: Attach payment method to customer FIRST (must be done before subscription creation)
            try:
                # Check if payment method is already attached
                try:
                    pm = stripe.PaymentMethod.retrieve(payment_method_id)
                    if not pm.customer:
                        # Not attached, attach it
                        stripe.PaymentMethod.attach(
                            payment_method_id,
                            customer=customer_id
                        )
                        app.logger.info(f"Attached payment method {payment_method_id} to customer {customer_id}")
                    else:
                        app.logger.info(f"Payment method {payment_method_id} already attached to customer {pm.customer}")
                except stripe.error.InvalidRequestError as e:
                    # Payment method might not exist or be in a different state
                    app.logger.error(f"Error retrieving payment method: {str(e)}")
                    # Try to attach anyway
                    try:
                        stripe.PaymentMethod.attach(
                            payment_method_id,
                            customer=customer_id
                        )
                        app.logger.info(f"Attached payment method {payment_method_id} to customer {customer_id} after error")
                    except Exception as attach_error:
                        app.logger.error(f"Failed to attach payment method: {str(attach_error)}")
                        raise
                
                # Step 2: Set as default payment method on customer (for future invoices)
                stripe.Customer.modify(
                    customer_id,
                    invoice_settings={
                        "default_payment_method": payment_method_id
                    }
                )
                app.logger.info(f"Set payment method {payment_method_id} as default for customer {customer_id}")
                
            except Exception as e:
                app.logger.error(f"Error setting up payment method: {str(e)}")
                return jsonify({
                    "error": {
                        "message": f"Failed to set up payment method: {str(e)}"
                    }
                }), 400
            
            # Step 3: Validate price ID
            price = stripe.Price.retrieve(price_id)
            if not price.active or price.type != "recurring":
                return jsonify({
                    "error": {
                        "message": f"Price {price_id} is not a valid recurring price."
                    }
                }), 400

            # Step 4: Create the subscription with the saved payment method
            # According to Stripe docs: https://docs.stripe.com/billing/subscriptions/overview#subscription-lifecycle
            # The payment method must be attached BEFORE creating the subscription
            # We create the subscription which will automatically create an invoice
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                default_payment_method=payment_method_id,
                payment_settings={
                    "save_default_payment_method": "on_subscription"
                },
                # Since we already collected payment via PaymentIntent, we can set payment_behavior
                # to allow incomplete, then we'll pay the invoice manually
                payment_behavior="allow_incomplete",
                metadata={
                    "portfolios": ", ".join(portfolios) if portfolios else "N/A",
                    "portfolio_count": str(len(portfolios)),
                    "price_id": price_id,
                    "payment_intent_id": payment_intent_id
                },
                expand=["latest_invoice"]
            )
            
            app.logger.info(f"Created subscription {subscription.id} with payment method {payment_method_id} for customer {customer_id}, status: {subscription.status}")
            
            # Step 5: Pay the subscription's initial invoice using the already-succeeded payment
            # The PaymentIntent already succeeded, so we need to mark the subscription invoice as paid
            # or pay it with the saved payment method
            if subscription.latest_invoice:
                invoice = subscription.latest_invoice
                if isinstance(invoice, str):
                    invoice = stripe.Invoice.retrieve(invoice, expand=["payment_intent"])
                
                # If invoice is open/unpaid, pay it with the saved payment method
                if invoice.status == "open" or invoice.status == "draft":
                    try:
                        # Finalize draft invoice if needed
                        if invoice.status == "draft":
                            invoice = stripe.Invoice.finalize_invoice(invoice.id)
                            app.logger.info(f"Finalized invoice {invoice.id}")
                        
                        # Pay the invoice using the saved payment method
                        paid_invoice = stripe.Invoice.pay(
                            invoice.id,
                            payment_method=payment_method_id
                        )
                        app.logger.info(f"Paid invoice {paid_invoice.id} for subscription {subscription.id}")
                        
                        # Refresh subscription to get updated status
                        subscription = stripe.Subscription.retrieve(subscription.id)
                        app.logger.info(f"Subscription {subscription.id} status after invoice payment: {subscription.status}")
                    except Exception as e:
                        app.logger.error(f"Error paying invoice: {str(e)}")
                        # Don't fail the request, but log the error
                        # The subscription might still work if Stripe handles it automatically
            
            # Verify subscription has the payment method set correctly
            if subscription.default_payment_method != payment_method_id:
                app.logger.warning(f"Subscription {subscription.id} default_payment_method is {subscription.default_payment_method}, expected {payment_method_id}")
                try:
                    subscription = stripe.Subscription.modify(
                        subscription.id,
                        default_payment_method=payment_method_id
                    )
                    app.logger.info(f"Updated subscription {subscription.id} default_payment_method to {payment_method_id}")
                except Exception as e:
                    app.logger.error(f"Failed to update subscription default_payment_method: {str(e)}")

            return jsonify({
                "subscriptionId": subscription.id,
                "status": subscription.status,
                "customerId": customer_id
            })

        except stripe.error.InvalidRequestError as e:
            return jsonify({
                "error": {
                    "type": "invalid_request_error",
                    "message": str(e),
                }
            }), 400
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            app.logger.error(f"Unexpected error in create_subscription: {str(e)}\n{error_trace}")
            return jsonify({
                "error": {
                    "message": f"Server error: {str(e)}",
                    "type": "server_error"
                }
            }), 500

    @app.route("/cancel-subscription", methods=["POST"])
    def cancel_subscription():
        """Cancel a Stripe subscription.
        
        Expected JSON body:
        - subscriptionId: The ID of the subscription to cancel
        """
        if not stripe.api_key:
            return jsonify({
                "error": {
                    "message": "Server not configured. Set STRIPE_SECRET_KEY environment variable."
                }
            }), 500

        data = request.get_json(silent=True) or {}
        subscription_id = data.get("subscriptionId")

        if not subscription_id:
            return jsonify({
                "error": {
                    "message": "Missing required field: subscriptionId"
                }
            }), 400

        try:
            # Cancel the subscription at the end of the current billing period
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )

            return jsonify({
                "subscriptionId": subscription.id,
                "status": subscription.status,
                "cancelAtPeriodEnd": subscription.cancel_at_period_end,
                "currentPeriodEnd": subscription.current_period_end,
            })

        except stripe.error.StripeError as e:
            return jsonify({
                "error": {
                    "type": e.error.type if hasattr(e, "error") else "stripe_error",
                    "message": e.user_message or str(e),
                }
            }), 400
        except Exception as e:
            app.logger.error(f"Unexpected error in cancel_subscription: {str(e)}")
            return jsonify({"error": {"message": "An unexpected error occurred."}}), 500

    @app.route("/list-subscriptions", methods=["GET"])
    def list_subscriptions():
        """List all subscriptions for a customer (optional)."""
        if not stripe.api_key:
            return jsonify({
                "error": {
                    "message": "Server not configured. Set STRIPE_SECRET_KEY environment variable."
                }
            }), 500

        customer_email = request.args.get("email")
        
        try:
            if customer_email:
                # Find customer by email
                customers = stripe.Customer.list(email=customer_email, limit=1)
                if not customers.data:
                    return jsonify({"subscriptions": []})
                
                subscriptions = stripe.Subscription.list(customer=customers.data[0].id)
            else:
                # List all subscriptions (limited for demo)
                subscriptions = stripe.Subscription.list(limit=10)
            
            return jsonify({
                "subscriptions": [{
                    "id": sub.id,
                    "status": sub.status,
                    "current_period_end": sub.current_period_end,
                    "portfolios": sub.metadata.get("portfolios", "N/A"),
                    "customer_email": sub.customer.email if hasattr(sub.customer, 'email') else "N/A"
                } for sub in subscriptions.data]
            })
        except Exception as e:
            return jsonify({"error": {"message": str(e)}}), 500

    return app


# Expose WSGI app at module level for Vercel (@vercel/python) to detect
# This ensures the serverless function can import `server.app`
app = create_app()

if __name__ == "__main__":
    # Optional: load .env if present
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    # Check if Stripe key is provided
    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not stripe_key:
        print("❌ ERROR: No Stripe secret key found!")
        print("📝 Please set your Stripe secret key (test or live):")
        print("   export STRIPE_SECRET_KEY=sk_test_your_key_here  # for test mode")
        print("   export STRIPE_SECRET_KEY=sk_live_your_key_here   # for live mode")
        print("   python server.py")
        print("\n🔗 Get your keys from:")
        print("   Test: https://dashboard.stripe.com/test/apikeys")
        print("   Live: https://dashboard.stripe.com/apikeys")
        exit(1)

    port = int(os.environ.get("PORT", "4242"))
    app = create_app()
    is_test_mode = stripe_key.startswith('sk_test_')
    mode_text = "TEST MODE" if is_test_mode else "LIVE MODE ⚠️  PRODUCTION"
    mode_emoji = "🧪" if is_test_mode else "🚀"
    print(f"🚀 Starting server on http://localhost:{port}")
    print(f"💳 Stripe {mode_emoji} {mode_text}")
    print(f"📄 Open http://localhost:{port} in your browser to see the payment page")
    app.run(host="0.0.0.0", port=port, debug=True)
