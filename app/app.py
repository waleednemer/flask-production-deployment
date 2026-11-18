
from flask import Flask, jsonify

app = Flask(__name__)

APP_VERSION = "7.0"


@app.route("/")
def home():
    return jsonify({
        "application": "flask-production",
        "message": "Welcome to DevOps Production!",
        "version": APP_VERSION,
        "status": "running"
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "healthy"
    })


@app.route("/version")
def version():
    return jsonify({
        "application": "flask-production",
        "version": APP_VERSION,
        "status": "running"
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
