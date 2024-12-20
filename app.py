from flask import Flask, request, jsonify
import stripe
import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Set Stripe secret key from environment
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Firebase Setup
cred = credentials.Certificate(os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY'))
firebase_admin.initialize_app(cred)
db = firestore.client()  # Firestore client

# Firestore Collection name
payments_collection = db.collection('payments')

# Stripe Webhook Secret
endpoint_secret = "whsec_55nwiw87lB8o55qX7gxJ2GRlcbzrdVz0"

@app.route('/create-payment-intent', methods=['POST'])
def create_payment_intent():
    try:
        data = request.json
        print("Data sent from Apple:", data)

        # Retrieve the amount in cents from the frontend
        amount = data.get('amount')
        currency = data.get('currency', 'usd')  # Default to USD if no currency is provided
        charity = data.get('charity')  # Extract charity information from the request

        # Validate the amount (ensure it's an integer and greater than 0)
        if not isinstance(amount, int) or amount <= 0:
            return jsonify({'error': 'Amount must be a positive integer in cents'}), 400

        if not amount:
            return jsonify({'error': 'Amount is required'}), 400

        # Create a PaymentIntent with the specified amount and currency
        intent = stripe.PaymentIntent.create(
            amount=amount,  # Amount is already in cents
            currency=currency,
            payment_method_types=['card'],  # Specify allowed payment methods (e.g., card, Apple Pay, etc.)
            capture_method='manual',  # Allow for manual capture (useful if you want to authorize and capture later)
        )

        # Store the payment intent details in Firestore
        payment_ref = payments_collection.document(intent.id)  # Use the PaymentIntent ID as the Firestore document ID
        payment_ref.set({
            'amount': intent.amount,
            'currency': intent.currency,
            'status': intent.status,  # Initial status
            'created_at': datetime.utcnow(),
            'payment_intent_id': intent.id,  # Store the PaymentIntent ID for reference
            'charity': charity  # Save the charity info in Firestore
        })

        # Return the client secret to the frontend
        return jsonify({'clientSecret': intent.client_secret})  # Return the clientSecret for frontend

    except stripe.error.StripeError as e:
        # Catch Stripe-specific errors
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        # Catch all other errors
        return jsonify({'error': str(e)}), 400

# Handle Stripe Webhook for Payment Success and Charge Success
@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    print("Received webhook")
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

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

    # Handle the event for successful charge (as a fallback or for different scenarios)
    if event['type'] == 'charge.succeeded':
        charge = event['data']['object']  # Contains the charge object
        handle_charge_succeeded(charge)

    return '', 200  # Respond to Stripe that the event was received successfully

def handle_payment_intent_succeeded(payment_intent):
    # Payment succeeded, you can update Firestore to mark the payment as successful
    print(f"Payment for {payment_intent['amount_received']} succeeded!")

    # Find the payment in Firestore by its payment_intent_id
    payment_ref = payments_collection.document(payment_intent['id'])
    payment_data = payment_ref.get()

    if payment_data.exists:
        # Update the status of the payment in Firestore
        payment_ref.update({
            'status': 'succeeded',
            'completed_at': datetime.utcnow()
        })
        print(f"Payment status updated to 'succeeded' for PaymentIntent {payment_intent['id']}")

def handle_charge_succeeded(charge):
    # Payment succeeded for charge, you can update Firestore to mark the payment as successful
    print(f"Charge for {charge['amount']} succeeded!")
    update_balance_in_firestore(charge['amount'])

    # Retrieve the payment intent from the charge object
    payment_ref = payments_collection.document(charge['payment_intent'])
    payment_data = payment_ref.get()

    if payment_data.exists:
        charity_name = payment_data.get('charity')  # Retrieve the charity name from the payment document

        # If charity name exists, update the charity's balance document
        if charity_name:
            update_charity_balance(charity_name, charge['amount'])

        # Update the status of the payment in Firestore
        payment_ref.update({
            'status': 'succeeded',
            'completed_at': datetime.utcnow()
        })
        print(f"Payment status updated to 'succeeded' for Charge {charge['id']}")

def update_balance_in_firestore(payment_amount):
    print("Attempted to update balance")
    # Reference to the 'mother' document in the 'charity' collection
    doc_ref = db.collection('charity').document('mother')

    # Get the current balance
    doc = doc_ref.get()
    
    if doc.exists:
        # Debugging: Print the document to see the structure
        print("Document data:", doc.to_dict())
        
        # Now safely access the balance field
        current_balance = doc.get('balance')  # Default to 0 if 'balance' field does not exist
        new_balance = current_balance + payment_amount  # Add payment amount to current balance
        
        # Update the balance field in the Firestore document
        doc_ref.update({
            'balance': new_balance
        })
        print(f"Balance updated to {new_balance} in Firestore (charity -> mother).")
    else:
        print("Document 'mother' does not exist in Firestore.")

def update_charity_balance(charity_name, payment_amount):
    print(f"Attempted to update {charity_name} balance")
    
    # Reference to the charity document in the 'charity' collection based on the charity name
    charity_doc_ref = db.collection('charity').document(charity_name)

    # Get the current balance for the specific charity
    doc = charity_doc_ref.get()
    
    if doc.exists:
        # Debugging: Print the document to see the structure
        print(f"Charity document data for {charity_name}:", doc.to_dict())
        
        # Safely access the balance field for the charity
        current_balance = doc.get('balance')  # Default to 0 if 'balance' field does not exist
        new_balance = current_balance + payment_amount  # Add payment amount to the current balance
        
        # Update the balance field in the specific charity document
        charity_doc_ref.update({
            'balance': new_balance
        })
        print(f"Balance updated to {new_balance} in Firestore (charity -> {charity_name}).")
    else:
        print(f"Document for charity {charity_name} does not exist in Firestore.")

    
if __name__ == '__main__':
    app.run(port=3000, debug=True)
