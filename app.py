import os
from flask import Flask, jsonify, request
import stripe
from dotenv import load_dotenv
from flask_cors import CORS

# Load environment variables from .env file
load_dotenv()

# Initialize the Flask app
app = Flask(__name__)

# Set up Stripe API key (loaded from environment variables)
stripe.api_key = os.getenv('STRIPE_API_KEY')

# Allow cross-origin requests (useful for development with different front-end ports)
CORS(app)

@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to ensure the app is running."""
    return jsonify({'status': 'healthy'}), 200

@app.route('/create-payment', methods=['POST'])
def create_payment_intent():
    try:
        # Get the payment amount and currency from the request
        data = request.json
        amount = data.get('amount')  # The amount should be in cents (e.g., $20 = 2000 cents)
        currency = data.get('currency', 'usd')  # Default to USD if no currency is provided

        if not amount:
            return jsonify({'error': 'Amount is required'}), 400

        # Create a payment intent with Stripe
        payment_intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            payment_method_types=['card'],  # Add other payment methods if needed (e.g., 'apple_pay', 'google_pay')
        )

        # Return the client secret to the front end
        return jsonify({'clientSecret': payment_intent.client_secret})

    except stripe.error.StripeError as e:
        # Stripe API error handling
        return jsonify(error=str(e.user_message)), 400
    except Exception as e:
        # General error handling
        return jsonify(error=str(e)), 500

if __name__ == '__main__':
    app.run(debug=True)