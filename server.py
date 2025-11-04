import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import stripe


def create_app() -> Flask:
    app = Flask(__name__, static_folder='.')
    CORS(app)

    # Configure Stripe using environment variable for security
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

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

    @app.route("/create-subscription", methods=["POST"])
    def create_subscription():
        """Create a Stripe Subscription and return the PaymentIntent client secret.

        Expected JSON body:
        - email: Customer email
        - name: Customer full name
        - priceId: Stripe Price ID (recurring)
        - portfolios: List of selected portfolio names (optional, for metadata)
        """
        if not stripe.api_key:
            return jsonify({
                "error": {
                    "message": "Server not configured. Set STRIPE_SECRET_KEY environment variable."
                }
            }), 500

        data = request.get_json(silent=True) or {}
        email = data.get("email")
        name = data.get("name")
        price_id = data.get("priceId")
        portfolios = data.get("portfolios", [])

        if not email or not name or not price_id:
            return jsonify({
                "error": {
                    "message": "Missing required fields: email, name, priceId"
                }
            }), 400

        try:
            # Validate price ID exists and is accessible with current API key mode
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
                # Price doesn't exist or wrong mode (test vs live mismatch)
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

            # Create the subscription in incomplete state
            # Stripe automatically creates a PaymentIntent for the subscription's invoice
            # when using payment_behavior="default_incomplete"
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{"price": price_id}],
                payment_behavior="default_incomplete",
                payment_settings={
                    "save_default_payment_method": "on_subscription"
                },
                expand=["latest_invoice.payment_intent"],  # Expand to get PaymentIntent details
                metadata={
                    "portfolios": ", ".join(portfolios) if portfolios else "N/A",
                    "portfolio_count": str(len(portfolios)),
                    "price_id": price_id
                }
            )

            # Get the client_secret from the subscription's PaymentIntent
            # The PaymentIntent is automatically created by Stripe for the invoice
            latest_invoice = subscription.latest_invoice
            
            # Handle both expanded and non-expanded invoice objects
            if isinstance(latest_invoice, str):
                # If it's just an ID, retrieve the invoice with PaymentIntent expanded
                invoice = stripe.Invoice.retrieve(latest_invoice, expand=["payment_intent"])
                payment_intent = invoice.payment_intent
            else:
                # Invoice is already expanded
                payment_intent = latest_invoice.payment_intent
            
            # If payment_intent is None, the invoice might not have a payment intent yet
            if payment_intent is None:
                app.logger.error(f"No PaymentIntent found for subscription {subscription.id}, invoice {latest_invoice.id if hasattr(latest_invoice, 'id') else latest_invoice}")
                return jsonify({
                    "error": {
                        "message": "PaymentIntent not available. Please try again."
                    }
                }), 500
            
            # Handle both expanded and non-expanded PaymentIntent objects
            if isinstance(payment_intent, str):
                # If it's just an ID, retrieve the PaymentIntent
                payment_intent = stripe.PaymentIntent.retrieve(payment_intent)
            
            # Ensure we have a client_secret
            if not hasattr(payment_intent, 'client_secret') or not payment_intent.client_secret:
                app.logger.error(f"No client_secret found for PaymentIntent {payment_intent.id}")
                return jsonify({
                    "error": {
                        "message": "PaymentIntent client secret not available. Please try again."
                    }
                }), 500
            
            client_secret = payment_intent.client_secret
            
            # Ensure PaymentIntent only accepts card payments (no Link)
            # Only modify if payment_method_types exists and is not already ["card"]
            if hasattr(payment_intent, 'payment_method_types'):
                current_types = payment_intent.payment_method_types
                if current_types and "card" not in current_types:
                    # If card is not in the list, add it
                    stripe.PaymentIntent.modify(
                        payment_intent.id,
                        payment_method_types=["card"]
                    )
                elif current_types and len(current_types) > 1 and "card" in current_types:
                    # If there are multiple types including card, restrict to card only
                    stripe.PaymentIntent.modify(
                        payment_intent.id,
                        payment_method_types=["card"]
                    )

            return jsonify({
                "subscriptionId": subscription.id,
                "clientSecret": client_secret,
                "customerId": customer.id,
            })

        except stripe.error.CardError as e:
            # Card was declined
            return jsonify({
                "error": {
                    "type": "card_error",
                    "message": e.user_message or "Your card was declined.",
                }
            }), 400
        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            return jsonify({
                "error": {
                    "type": "rate_limit_error",
                    "message": "Too many requests. Please try again later.",
                }
            }), 429
        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            return jsonify({
                "error": {
                    "type": "invalid_request_error",
                    "message": str(e),
                }
            }), 400
        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            return jsonify({
                "error": {
                    "type": "authentication_error",
                    "message": "Authentication with payment provider failed.",
                }
            }), 401
        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            return jsonify({
                "error": {
                    "type": "api_connection_error",
                    "message": "Network error. Please try again.",
                }
            }), 502
        except stripe.error.StripeError as e:
            # Generic Stripe error
            return jsonify({
                "error": {
                    "type": "stripe_error",
                    "message": e.user_message or str(e),
                }
            }), 400
        except Exception as e:
            # Something else happened, completely unrelated to Stripe
            import traceback
            error_trace = traceback.format_exc()
            app.logger.error(f"Unexpected error in create_subscription: {str(e)}\n{error_trace}")
            # Return detailed error for debugging
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
