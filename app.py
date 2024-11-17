from flask import Flask, request, jsonify
import stripe
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Set Stripe secret key from environment
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# You can also store your publishable key in .env
publishable_key = os.getenv('STRIPE_PUBLISHABLE_KEY')

endpoint_secret = "whsec_55nwiw87lB8o55qX7gxJ2GRlcbzrdVz0"

# Create Payment Intent (for initial payment setup)
@app.route('/create-payment-intent', methods=['POST'])
def create_payment_intent():
    try:
        data = request.json
        amount = data.get('amount')
        currency = data.get('currency', 'usd')  # Default to USD if no currency is provided

        if not amount:
            return jsonify({'error': 'Amount is required'}), 400

        # Create a PaymentIntent with the specified amount and currency
        intent = stripe.PaymentIntent.create(
            amount=int(amount),  # Amount should be in cents
            currency=currency,
            payment_method_types=['card'],  # Specify allowed payment methods (e.g., card, Apple Pay, etc.)
            capture_method='manual',  # Allow for manual capture (useful if you want to authorize and capture later)
        )

        return jsonify({'clientSecret': intent.client_secret})  # Return the clientSecret for frontend

    except stripe.error.StripeError as e:
        # Catch Stripe-specific errors
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        # Catch all other errors
        return jsonify({'error': str(e)}), 400


@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    print("recieved webhook")
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    # Print to debug
    print(f"Received payload: {payload}")
    print(f"Received Stripe-Signature: {sig_header}")
    
    # Verify the webhook signature to ensure the request is from Stripe
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        print(f"Invalid payload: {e}")
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print(f"Invalid signature: {e}")
        return 'Invalid signature', 400

    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']  # Contains the payment intent object
        handle_payment_intent_succeeded(payment_intent)
    
    elif event['type'] == 'payment_intent.failed':
        payment_intent = event['data']['object']  # Contains the payment intent object
        handle_payment_intent_failed(payment_intent)

    # Other event types can be added here as needed

    return '', 200  # Respond to Stripe that the event was received successfully

def handle_payment_intent_succeeded(payment_intent):
    # Payment succeeded, you can update your database to mark the payment as successful
    print(f"Payment for {payment_intent['amount_received']} succeeded!")

    # Example: Update order status in your database
    # order = Order.query.filter_by(payment_intent_id=payment_intent['id']).first()
    # if order:
    #     order.status = 'paid'
    #     db.session.commit()

    # Optionally, send a confirmation email or notify the user
    # send_email(order.user_email, 'Payment Successful', 'Your payment was successful!')

def handle_payment_intent_failed(payment_intent):
    # Payment failed, you can update your database to mark the payment as failed
    print(f"Payment for {payment_intent['amount_received']} failed!")

    # Example: Update order status in your database
    # order = Order.query.filter_by(payment_intent_id=payment_intent['id']).first()
    # if order:
    #     order.status = 'failed'
    #     db.session.commit()

    # Optionally, notify the user about the failure
    # send_email(order.user_email, 'Payment Failed', 'Your payment failed. Please try again.')


if __name__ == '__main__':
    app.run(port=5000, debug=True)
