import os
from flask import Flask, jsonify, request

app = Flask(__name__)

# Basic health check endpoint to keep Render awake
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "Daraja API backend is running successfully!"}), 200

# M-Pesa STK Push Callback Endpoint
@app.route("/api/v1/mpesa/callback", methods=["POST"])
def mpesa_callback():
    callback_data = request.get_json()
    
    # Log or process the M-Pesa response payload here
    print("Received M-Pesa Callback:", callback_data)
    
    # Always respond back to Safaricom quickly to acknowledge receipt
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted Successfully"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
