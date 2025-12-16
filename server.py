import os
from decimal import Decimal, ROUND_HALF_UP
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import stripe
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Load environment variables from .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, skip loading .env file

# Swiss VAT (TVA) rate for subscriptions (8.1%)
VAT_RATE = Decimal('0.081')


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
           request.path.startswith('/create-payment-intent') or \
           request.path.startswith('/create-checkout-session') or \
           request.path.startswith('/verify-subscription') or \
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

    # New route to expose the mobile app download landing page with store links and QR codes.
    @app.route('/app-link')
    def app_link():
        """Serve the dedicated mobile app download page with store badges and QR codes."""
        return send_from_directory('.', 'openfolio-app-link.html')
    
    @app.route('/profile')
    def profile():
        """Serve the risk profile questionnaire page."""
        return send_from_directory('.', 'profile.html')
    
    def send_profile_email(profile_data):
        """
        Send profile form submission via email notification.
        
        Requires environment variables:
        - SMTP_HOST: SMTP server hostname (e.g., smtp.gmail.com)
        - SMTP_PORT: SMTP server port (default: 587)
        - SMTP_USER: Sender email address
        - SMTP_PASSWORD: Sender email password or app-specific password
        - PROFILE_NOTIFICATION_EMAIL: Comma-separated recipient emails
          (default: "bastien@balder-app.com,philippe.beckers@sparrtner.ch")
        """
        try:
            # Get SMTP configuration from environment variables
            smtp_host = os.environ.get("SMTP_HOST", "")
            smtp_port = int(os.environ.get("SMTP_PORT", "587"))
            smtp_user = os.environ.get("SMTP_USER", "")
            smtp_password = os.environ.get("SMTP_PASSWORD", "")
            recipients_raw = os.environ.get(
                "PROFILE_NOTIFICATION_EMAIL",
                "bastien@balder-app.com,philippe.beckers@sparrtner.ch",
            )
            # Parse and clean recipient list
            recipient_emails = [e.strip() for e in recipients_raw.split(",") if e.strip()]
            
            # Validate required SMTP configuration
            if not smtp_host or not smtp_user or not smtp_password:
                app.logger.error("SMTP configuration missing. Required: SMTP_HOST, SMTP_USER, SMTP_PASSWORD")
                return False
            if not recipient_emails:
                app.logger.error("No valid recipient emails configured in PROFILE_NOTIFICATION_EMAIL.")
                return False
            
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "New OpenFolio Risk Profile Submission"
            msg['From'] = smtp_user
            msg['To'] = ", ".join(recipient_emails)
            
            # Format profile data
            submission_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Create HTML email body
            html_body = f"""
            <html>
              <head></head>
              <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #1a1a1a;">New OpenFolio Risk Profile Submission</h2>
                <p><strong>Submission Date:</strong> {submission_date}</p>
                
                <table style="border-collapse: collapse; width: 100%; max-width: 600px; margin: 20px 0;">
                  <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold; width: 40%;">Market Knowledge</td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{profile_data.get('marketKnowledge', 'N/A')}</td>
                  </tr>
                  <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Instrument Knowledge</td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{profile_data.get('instrumentKnowledge', 'N/A')}</td>
                  </tr>
                  <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Fluctuation Tolerance</td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{profile_data.get('fluctuationTolerance', 'N/A')}</td>
                  </tr>
                  <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Max Annual Loss</td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{profile_data.get('maxAnnualLoss', 'N/A')}</td>
                  </tr>
                  <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Investment Goal</td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{profile_data.get('investmentGoal', 'N/A')}</td>
                  </tr>
                  <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Liquidity Need</td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{profile_data.get('liquidityNeed', 'N/A')}</td>
                  </tr>
                  <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Regular Investment</td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{profile_data.get('regularInvestment', 'N/A')}</td>
                  </tr>
                  <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Initial Amount</td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{profile_data.get('initialAmount', 'N/A')} CHF</td>
                  </tr>
                  <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Time Horizon</td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{profile_data.get('timeHorizon', 'N/A')}</td>
                  </tr>
                </table>
                
                {f'<p><strong>User Email:</strong> {profile_data.get("email", "Not provided")}</p>' if profile_data.get('email') else ''}
                {f'<p><strong>User Name:</strong> {profile_data.get("name", "Not provided")}</p>' if profile_data.get('name') else ''}
              </body>
            </html>
            """
            
            # Create plain text version
            text_body = f"""
New OpenFolio Risk Profile Submission

Submission Date: {submission_date}

Profile Details:
- Market Knowledge: {profile_data.get('marketKnowledge', 'N/A')}
- Instrument Knowledge: {profile_data.get('instrumentKnowledge', 'N/A')}
- Fluctuation Tolerance: {profile_data.get('fluctuationTolerance', 'N/A')}
- Max Annual Loss: {profile_data.get('maxAnnualLoss', 'N/A')}
- Investment Goal: {profile_data.get('investmentGoal', 'N/A')}
- Liquidity Need: {profile_data.get('liquidityNeed', 'N/A')}
- Regular Investment: {profile_data.get('regularInvestment', 'N/A')}
- Initial Amount: {profile_data.get('initialAmount', 'N/A')} CHF
- Time Horizon: {profile_data.get('timeHorizon', 'N/A')}
"""
            if profile_data.get('email'):
                text_body += f"- User Email: {profile_data.get('email')}\n"
            if profile_data.get('name'):
                text_body += f"- User Name: {profile_data.get('name')}\n"
            
            # Attach both versions
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email via SMTP
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()  # Enable TLS encryption
                server.login(smtp_user, smtp_password)
                # send to all configured recipients
                server.sendmail(smtp_user, recipient_emails, msg.as_string())
            
            app.logger.info(f"Profile submission email sent successfully to: {', '.join(recipient_emails)}")
            return True
            
        except Exception as e:
            app.logger.error(f"Failed to send profile email: {str(e)}")
            return False
    
    @app.route("/submit-profile", methods=["POST"])
    def submit_profile():
        """Handle profile form submissions and send email notification."""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({
                    "error": {
                        "message": "No data provided"
                    }
                }), 400
            
            # Extract profile data
            profile_data = {
                'marketKnowledge': data.get('marketKnowledge', ''),
                'instrumentKnowledge': data.get('instrumentKnowledge', ''),
                'fluctuationTolerance': data.get('fluctuationTolerance', ''),
                'maxAnnualLoss': data.get('maxAnnualLoss', ''),
                'investmentGoal': data.get('investmentGoal', ''),
                'liquidityNeed': data.get('liquidityNeed', ''),
                'regularInvestment': data.get('regularInvestment', ''),
                'initialAmount': data.get('initialAmount', ''),
                'timeHorizon': data.get('timeHorizon', ''),
                'email': data.get('email', ''),
                'name': data.get('name', ''),
            }
            
            # Validate that at least some profile data is present
            required_fields = ['marketKnowledge', 'instrumentKnowledge', 'fluctuationTolerance', 
                              'maxAnnualLoss', 'investmentGoal']
            missing_fields = [field for field in required_fields if not profile_data.get(field)]
            
            if missing_fields:
                return jsonify({
                    "error": {
                        "message": f"Missing required fields: {', '.join(missing_fields)}"
                    }
                }), 400
            
            # Send email
            email_sent = send_profile_email(profile_data)
            
            if email_sent:
                return jsonify({
                    "success": True,
                    "message": "Profile submitted successfully"
                }), 200
            else:
                # Still return success to user, but log the error
                app.logger.error("Email sending failed but profile data was received")
                return jsonify({
                    "success": True,
                    "message": "Profile received (email notification may have failed)"
                }), 200
                
        except Exception as e:
            app.logger.error(f"Error in submit_profile: {str(e)}")
            return jsonify({
                "error": {
                    "message": "Internal server error. Please try again later."
                }
            }), 500
    
    @app.route('/assets/<path:filename>')
    def serve_assets(filename):
        """Serve static assets from the assets folder."""
        return send_from_directory('assets', filename)

    @app.route("/health", methods=["GET"])
    def health():
        """Basic health check endpoint."""
        return jsonify({"status": "ok", "stripe_configured": bool(stripe.api_key)}), 200

    def get_or_create_price(portfolio_count, billing_period, base_product_id):
        """Get or create a Stripe price with the correct discount based on portfolio count and billing period.
        
        Args:
            portfolio_count: Number of portfolios (1-4)
            billing_period: 'monthly', 'biannual', or 'annual'
            base_product_id: The base product ID to use
            
        Returns:
            Stripe Price object
        """
        # Discount configuration (matches frontend) - all amounts in CHF (HT)
        base_price = Decimal('180.00')  # CHF per portfolio for 6 months (hors TVA)
        volume_discounts = {
            1: Decimal('0.00'),  # 0% discount
            2: Decimal('0.10'),  # 10% discount
            3: Decimal('0.20'),  # 20% discount
            4: Decimal('0.30'),  # 30% discount
        }
        annual_discount = Decimal('0.10')  # 10% additional discount for annual billing

        # Calculate totals excluding VAT
        if billing_period == 'annual':
            billing_multiplier = Decimal('2')  # 360 CHF per portfolio for 1 year
        elif billing_period == 'monthly':
            billing_multiplier = Decimal('1') / Decimal('6')  # 30 CHF per portfolio per month
        else:  # biannual
            billing_multiplier = Decimal('1')  # 180 CHF per portfolio for 6 months
        
        original_total_ex_vat = (base_price * Decimal(portfolio_count) * billing_multiplier)
        volume_discount = volume_discounts.get(portfolio_count, Decimal('0'))
        discounted_total_ex_vat = (original_total_ex_vat * (Decimal('1') - volume_discount))

        if billing_period == 'annual':
            discounted_total_ex_vat *= (Decimal('1') - annual_discount)

        # Round HT totals to centime precision
        original_total_ex_vat = original_total_ex_vat.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        discounted_total_ex_vat = discounted_total_ex_vat.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # Apply VAT (TVA 8.1%)
        vat_amount = (discounted_total_ex_vat * VAT_RATE).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_with_vat = (discounted_total_ex_vat + vat_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        original_total_incl_vat = (original_total_ex_vat * (Decimal('1') + VAT_RATE)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # Convert to cents for Stripe (amount TTC)
        amount_cents = int((total_with_vat * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

        # Create lookup key for price identification (include VAT marker to avoid legacy prices)
        lookup_key = f"openfolio_{billing_period}_{portfolio_count}_portfolios_vat81"
        
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
            elif billing_period == 'monthly':
                interval = 'month'
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
                    'original_amount_ex_vat': str(original_total_ex_vat),
                    'original_amount_incl_vat': str(original_total_incl_vat),
                    'discounted_amount_ex_vat': str(discounted_total_ex_vat),
                    'vat_rate': str(VAT_RATE),
                    'vat_amount': str(vat_amount),
                    'total_amount_incl_vat': str(total_with_vat),
                    'volume_discount': str(volume_discount),
                    'annual_discount_applied': str(billing_period == 'annual')
                },
                nickname=f"OpenFolio {billing_period.capitalize()} - {portfolio_count} portfolio{'s' if portfolio_count > 1 else ''}"
            )
            app.logger.info(
                "Created new price %s for %s portfolios (%s billing) - total TTC: %s CHF (HT: %s CHF, TVA: %s CHF)",
                price.id,
                portfolio_count,
                billing_period,
                total_with_vat,
                discounted_total_ex_vat,
                vat_amount,
            )
            return price
        except Exception as e:
            app.logger.error(f"Error creating price: {str(e)}")
            raise

    @app.route("/create-subscription-incomplete", methods=["POST"])
    def create_subscription_incomplete():
        """Create a subscription with incomplete status. PaymentIntent will be created automatically by Stripe.
        
        This follows Stripe's recommended flow to avoid double charging:
        1. Create subscription with payment_behavior=default_incomplete
        2. Stripe automatically creates PaymentIntent for the first invoice
        3. Confirm that PaymentIntent on frontend
        4. Subscription becomes active after payment succeeds
        
        Expected JSON body:
        - email: Customer email
        - name: Customer full name
        - priceId: Stripe Price ID (recurring) OR portfolioCount and billingPeriod to create price dynamically
        - portfolios: List of selected portfolio names (optional, for metadata)
        - portfolioCount: Number of portfolios (1-4) - used if priceId not provided
        - billingPeriod: 'biannual' or 'annual' - used if priceId not provided
        
        Returns:
        - clientSecret: PaymentIntent client secret from subscription's first invoice
        - customerId: Customer ID (created or existing)
        - priceId: The price ID used
        - subscriptionId: Subscription ID (status will be 'incomplete' until payment)
        - paymentIntentId: PaymentIntent ID to confirm
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
                
                if billing_period not in ['monthly', 'biannual', 'annual']:
                    return jsonify({
                        "error": {
                            "message": "Billing period must be 'monthly', 'biannual', or 'annual'"
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

            # Create subscription with payment_behavior=default_incomplete
            # This is Stripe's recommended approach to avoid double charging
            # Stripe will automatically create a PaymentIntent for the first invoice
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{"price": price_id}],
                payment_behavior="default_incomplete",  # Creates PaymentIntent automatically
                collection_method="charge_automatically",  # Force card payment, not invoice payment
                payment_settings={
                    "save_default_payment_method": "on_subscription"
                },
                metadata={
                    "portfolios": ", ".join(portfolios) if portfolios else "N/A",
                    "portfolio_count": str(len(portfolios)),
                    "price_id": price_id
                },
                expand=["latest_invoice.payment_intent"]
            )
            
            app.logger.info(f"Created subscription {subscription.id} with incomplete status for customer {customer.id}")
            
            # Extract PaymentIntent from the subscription's first invoice
            invoice = subscription.latest_invoice
            if isinstance(invoice, str):
                invoice = stripe.Invoice.retrieve(invoice, expand=["payment_intent"])
            
            payment_intent_id = None
            client_secret = None
            
            # Get PaymentIntent from invoice
            if invoice.payment_intent:
                if isinstance(invoice.payment_intent, str):
                    payment_intent_id = invoice.payment_intent
                    # Retrieve PaymentIntent to get client_secret
                    payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
                    client_secret = payment_intent.client_secret
                else:
                    # PaymentIntent is already expanded
                    payment_intent_id = invoice.payment_intent.id
                    client_secret = invoice.payment_intent.client_secret
            
            if not client_secret or not payment_intent_id:
                return jsonify({
                    "error": {
                        "message": "Failed to create PaymentIntent for subscription. Please try again."
                    }
                }), 500

            return jsonify({
                "clientSecret": client_secret,
                "customerId": customer.id,
                "priceId": price_id,
                "subscriptionId": subscription.id,
                "paymentIntentId": payment_intent_id
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

    @app.route("/verify-subscription", methods=["POST"])
    def verify_subscription():
        """Verify that a subscription's payment was successful and subscription is active.
        
        This endpoint is called after the PaymentIntent is confirmed on the frontend.
        It verifies the subscription status and returns the final subscription details.
        
        Expected JSON body:
        - subscriptionId: Subscription ID to verify
        - paymentIntentId: PaymentIntent ID that was confirmed (optional, for verification)
        
        Returns:
        - subscriptionId: Subscription ID
        - status: Subscription status (should be 'active' if payment succeeded)
        - customerId: Customer ID
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
        
        subscription_id = data.get("subscriptionId") if data else None
        payment_intent_id = data.get("paymentIntentId") if data else None

        if not subscription_id:
            return jsonify({
                "error": {
                    "message": "Missing required field: subscriptionId"
                }
            }), 400

        try:
            # Retrieve the subscription
            subscription = stripe.Subscription.retrieve(subscription_id, expand=["latest_invoice.payment_intent"])
            
            # Verify payment if PaymentIntent ID provided
            if payment_intent_id:
                payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
                if payment_intent.status != "succeeded":
                    return jsonify({
                        "error": {
                            "message": f"PaymentIntent {payment_intent_id} has not succeeded. Status: {payment_intent.status}"
                        }
                    }), 400
            
            # Check subscription status
            if subscription.status == "active":
                app.logger.info(f"Subscription {subscription_id} is active after payment")
            elif subscription.status == "incomplete":
                # Payment might still be processing
                app.logger.info(f"Subscription {subscription_id} is still incomplete, payment may be processing")
            else:
                app.logger.warning(f"Subscription {subscription_id} has unexpected status: {subscription.status}")

            return jsonify({
                "subscriptionId": subscription.id,
                "status": subscription.status,
                "customerId": subscription.customer,
                "defaultPaymentMethod": subscription.default_payment_method
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
            app.logger.error(f"Unexpected error in verify_subscription: {str(e)}\n{error_trace}")
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

    @app.route("/create-checkout-session", methods=["POST"])
    def create_checkout_session():
        """Create a Stripe Checkout Session for subscription payment.

        This redirects the user to a Stripe-hosted payment page with the invoice.
        Upon successful payment, the subscription is automatically activated.

        Expected JSON body:
        - email: Customer email
        - name: Customer full name
        - portfolioCount: Number of portfolios (1-4)
        - billingPeriod: 'biannual' or 'annual'
        - portfolios: List of selected portfolio names (optional, for metadata)

        Returns:
        - url: Stripe Checkout Session URL to redirect to
        - sessionId: Checkout Session ID
        """
        if not stripe.api_key:
            return jsonify({
                "error": {
                    "message": "Server not configured. Set STRIPE_SECRET_KEY environment variable."
                }
            }), 500

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
            # Get base product ID
            base_product_id = "prod_TMSfbpU4NW2fRK"

            # Validate portfolio count and billing period
            if portfolio_count < 1 or portfolio_count > 4:
                return jsonify({
                    "error": {
                        "message": "Portfolio count must be between 1 and 4"
                    }
                }), 400

            if billing_period not in ['monthly', 'biannual', 'annual']:
                return jsonify({
                    "error": {
                        "message": "Billing period must be 'monthly', 'biannual', or 'annual'"
                    }
                }), 400

            # Get or create price based on portfolio count and billing period
            price = get_or_create_price(portfolio_count, billing_period, base_product_id)

            # Check if a customer with this email already exists
            existing_customers = stripe.Customer.list(email=email, limit=1)

            if existing_customers.data:
                customer = existing_customers.data[0]
                # Update the customer's name if it has changed
                if customer.name != name:
                    customer = stripe.Customer.modify(customer.id, name=name)
            else:
                # Create a new customer
                customer = stripe.Customer.create(
                    email=email,
                    name=name,
                    metadata={
                        "selected_portfolios": ", ".join(portfolios) if portfolios else "N/A"
                    }
                )

            # Get the domain from the request or use a default
            # Vercel provides the host in request headers
            domain = request.headers.get('origin') or request.host_url.rstrip('/')

            # Create Checkout Session
            checkout_session = stripe.checkout.Session.create(
                customer=customer.id,
                mode='subscription',
                line_items=[{
                    'price': price.id,
                    'quantity': 1,
                }],
                # Redirect to the App Store page after successful payment
                # Note: Stripe will interpolate {CHECKOUT_SESSION_ID}, but we don't need it for this redirect
                success_url='https://openfolio-payment.vercel.app/app-link',
                cancel_url=domain + '/payment?canceled=true',
                metadata={
                    "portfolios": ", ".join(portfolios) if portfolios else "N/A",
                    "portfolio_count": str(len(portfolios)),
                    "billing_period": billing_period
                },
                subscription_data={
                    "metadata": {
                        "portfolios": ", ".join(portfolios) if portfolios else "N/A",
                        "portfolio_count": str(len(portfolios)),
                        "billing_period": billing_period
                    }
                },
                # Auto-activate subscription upon successful payment
                payment_method_collection='always',
            )

            app.logger.info(f"Created Checkout Session {checkout_session.id} for customer {customer.id}")

            return jsonify({
                "url": checkout_session.url,
                "sessionId": checkout_session.id
            })

        except stripe.error.StripeError as e:
            return jsonify({
                "error": {
                    "type": getattr(e, 'type', 'stripe_error'),
                    "message": e.user_message or str(e),
                }
            }), 400
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            app.logger.error(f"Unexpected error in create_checkout_session: {str(e)}\n{error_trace}")
            return jsonify({
                "error": {
                    "message": f"Server error: {str(e)}",
                    "type": "server_error"
                }
            }), 500

    return app


# Expose WSGI app at module level for Vercel (@vercel/python) to detect
# This ensures the serverless function can import `server.app`
app = create_app()

if __name__ == "__main__":
    # .env file is already loaded at module level above

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