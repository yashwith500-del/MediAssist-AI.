
from flask import Flask, jsonify, request, send_from_directory
from pathlib import Path

if __package__:
    from .ai_assistant import get_ai_response, is_ai_ready
else:
    from ai_assistant import get_ai_response, is_ai_ready

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/css/<path:filename>")
def css_files(filename):
    return send_from_directory(FRONTEND_DIR / "css", filename)


@app.route("/js/<path:filename>")
def js_files(filename):
    return send_from_directory(FRONTEND_DIR / "js", filename)


@app.route("/api/status", methods=["GET"])
def status():

    return jsonify({
        "project": "MediAssist AI",
        "status": "online",
        "gemini_connected": is_ai_ready(),
        "message": "Backend is running."
    })


@app.route("/api/vitals", methods=["GET"])
def vitals():

    # Temporary sample values.
    # These are NOT actual hardware readings.

    return jsonify({
        "mode": "SIMULATED",
        "heart_rate": 75,
        "temperature": 36.8,
        "spo2": 98,
        "message": "Sample data only. Not real measurements."
    })


@app.route("/api/chat", methods=["POST"])
def chat():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Invalid request format."
        }), 400

    question = data.get("question", "")

    if not isinstance(question, str) or not question.strip():
        return jsonify({
            "error": "Please enter a valid question."
        }), 400

    if len(question) > 10000:
        return jsonify({
            "error": "Your question is too long."
        }), 400

    if not is_ai_ready():
        return jsonify({
            "error": "Gemini API key is missing. Check your .env file."
        }), 503

    history = data.get("history", [])

    if not isinstance(history, list):
        history = []

    answer = get_ai_response(
        question=question,
        history=history
    )

    return jsonify({
        "answer": answer,
        "mode": "GEMINI_AI"
    })


if __name__ == "__main__":

    print("================================")
    print("       MEDIASSIST AI")
    print("================================")
    print("Backend: Running")
    print("Gemini:", "Configured" if is_ai_ready() else "Not configured")
    print("Frontend:", FRONTEND_DIR)
    print("================================")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
