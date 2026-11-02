import os
import requests
import base64
from datetime import datetime
from flask import Flask, jsonify, request

app = Flask(__name__)

# Helper function to generate Safaricom Daraja OAuth Access Token
def generate_access_token():
    consumer_key = os.environ.get("DARAJA_CONSUMER_KEY")
    consumer_secret = os.environ.get("DARAJA_CONSUMER_SECRET")
    env = os.environ.get("DARAJA_ENV", "sandbox")
    
    base_url = "https://sandbox.safaricom.co.ke" if env == "sandbox" else "https://api.safaricom.co.ke"
    api_url = f"{base_url}/oauth/v1/generate?grant_type=client_credentials"
    
    r = requests.get(api_url, auth=(consumer_key, consumer_secret))
    
    if r.status_code == 200:
        return r.json().get("access_token")
    return None

# 1. Base Health Check Endpoint (Keeps Render awake)
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "Online",
        "service": "Blessed Hotek Daraja Backend",
        "environment": os.environ.get("DARAJA_ENV", "sandbox")
    }), 200

# 2. Trigger STK Push (Initiate Payment Prompt on Guest's Phone)
@app.route("/api/v1/mpesa/stkpush", methods=["POST"])
def stk_push():
    data = request.get_json()
    phone_number = data.get("phone")  # Format: 2547XXXXXXXX
    amount = data.get("amount")       # E.g., 10, 500, etc.
    account_ref = data.get("account_reference", "Blessed Hotek")
    
    if not phone_number or not amount:
        return jsonify({"error": "Phone number and amount are required"}), 400

    access_token = generate_access_token()
    if not access_token:
        return jsonify({"error": "Failed to generate Daraja access token"}), 500

    env = os.environ.get("DARAJA_ENV", "sandbox")
    base_url = "https://sandbox.safaricom.co.ke" if env == "sandbox" else "https://api.safaricom.co.ke"
    api_url = f"{base_url}/mpesa/stkpush/v1/processurl"

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    shortcode = os.environ.get("DARAJA_SHORTCODE", "174379")
    passkey = os.environ.get("DARAJA_PASSKEY")

    # Generate Password
    string_to_encode = shortcode + passkey + timestamp
    password = base64.b64encode(string_to_encode.encode()).decode('utf-8')

    # Automatically construct callback URL based on your Render deployment
    callback_url = f"https://daraja-mpesa-backend.onrender.com/api/v1/mpesa/callback"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone_number,
        "PartyB": shortcode,
        "PhoneNumber": phone_number,
        "CallBackURL": callback_url,
        "AccountReference": account_ref,
        "TransactionDesc": "Hotel Payment"
    }

    response = requests.post(api_url, json=payload, headers=headers)
    return jsonify(response.json()), response.status_code

# 3. M-Pesa Callback Endpoint (Receives payment confirmation from Safaricom)
@app.route("/api/v1/mpesa/callback", methods=["POST"])
def mpesa_callback():
    callback_data = request.get_json()
    
    # Safaricom sends nested JSON structure on payment success/failure
    try:
        stk_callback = callback_data.get("Body", {}).get("stkCallback", {})
        result_code = stk_callback.get("ResultCode")
        result_desc = stk_callback.get("ResultDesc")
        merchant_request_id = stk_callback.get("MerchantRequestID")
        checkout_request_id = stk_callback.get("CheckoutRequestID")
        
        if result_code == 0:
            # Payment Successful! Extract metadata items (Receipt number, amount, phone)
            callback_metadata = stk_callback.get("CallbackMetadata", {}).get("Item", [])
            receipt_number = None
            for item in callback_metadata:
                if item.get("Name") == "MpesaReceiptNumber":
                    receipt_number = item.get("Value")
            
            print(f"SUCCESS: Payment received! Receipt: {receipt_number}, RequestID: {checkout_request_id}")
            # TODO: Update your database / hotel booking status here to 'Paid'
            
        else:
            print(f"FAILED / CANCELLED: {result_desc} (Code: {result_code})")
            # TODO: Handle failed or cancelled payment on your frontend/database
            
    except Exception as e:
        print(f"Error parsing callback: {str(e)}")

    # Always respond back to Safaricom quickly to acknowledge receipt of webhook
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted Successfully"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
