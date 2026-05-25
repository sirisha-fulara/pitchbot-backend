import os
import jwt
import datetime
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from gemini_config import (
    generate_pitch,
    grade_pitch,
    refine_pitch,
    competitor_extraction,
    differentiaiting_factor,
    generate_headline,
)
from export_utils import create_ppt, create_pdf
from custom_nlp import audience_alignment, buzzword_density, rewrite_in_persona
from db import (
    init_db,
    init_users_table,
    save_pitch,
    get_pitch_history,
    get_pitch_by_id,
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_pitches,
    get_user_stats,
    verify_password,
)

load_dotenv()
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

JWT_SECRET = os.getenv("JWT_SECRET", "pitchbot_secret_change_in_prod")
JWT_EXPIRY_HOURS = 24

init_db()
init_users_table()


#jwt helper
def make_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_token(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except:
        return None


def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return jsonify({"error": "Authentication required."}), 401
        payload = decode_token(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token."}), 401
        request.user_id = payload["user_id"]
        return f(*args, **kwargs)

    return decorated


def optional_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        payload = decode_token(token) if token else None
        request.user_id = payload["user_id"] if payload else None
        return f(*args, **kwargs)

    return decorated

#auth routes
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not username or not email or not password:
        return jsonify({"error": "All fields are required."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    user_id = create_user(username, email, password)
    if not user_id:
        return jsonify({"error": "Email or username already exists."}), 409

    token = make_token(user_id)
    return jsonify(
        {"token": token, "user": {"id": user_id, "username": username, "email": email}}
    )


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid email or password."}), 401

    token = make_token(user["id"])
    return jsonify(
        {
            "token": token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
            },
        }
    )


@app.route("/api/auth/me", methods=["GET"])
@auth_required
def me():
    user = get_user_by_id(request.user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404
    return jsonify({"user": user})


#pitch routes
@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json()
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    style = data.get("style", "corporate")
    if not title or not description:
        return jsonify({"error": "Title and description are required."}), 400
    pitch = generate_pitch(title, description, style)
    return jsonify({"pitch": pitch, "title": title, "style": style})


@app.route("/api/grade", methods=["POST"])
def grade():
    data = request.get_json()
    pitch = data.get("pitch", "")
    if not pitch:
        return jsonify({"error": "Pitch text required."}), 400
    return jsonify({"grading": grade_pitch(pitch)})


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    pitch = data.get("pitch", "")
    title = data.get("title", "")
    description = data.get("description", "")
    include_competitors = data.get("include_competitors", True)
    if not pitch:
        return jsonify({"error": "Pitch text required."}), 400
    audience = audience_alignment(pitch)
    buzzword = buzzword_density(pitch)
    headline = generate_headline(title, description, pitch)
    persona = rewrite_in_persona(pitch)
    competitors, difference = [], ""
    if include_competitors:
        competitors = competitor_extraction(pitch)
        difference = differentiaiting_factor(pitch, competitors)
    return jsonify(
        {
            "audience_alignment": audience,
            "buzzword_density": buzzword,
            "persona": persona,
            "headline": headline,
            "competitors": competitors,
            "differentiator": difference,
        }
    )


@app.route("/api/refine", methods=["POST"])
def refine():
    data = request.get_json()
    pitch = data.get("pitch", "")
    feedback = data.get("feedback", "Make it more concise and impactful")
    if not pitch:
        return jsonify({"error": "Pitch text required."}), 400
    return jsonify({"pitch": refine_pitch(pitch, feedback)})


@app.route("/api/export", methods=["POST"])
def export():
    data = request.get_json()
    title = data.get("title", "pitch")
    pitch = data.get("pitch", "")
    fmt = data.get("format", "pdf")
    if not pitch:
        return jsonify({"error": "Pitch text required."}), 400
    filename = create_ppt(title, pitch) if fmt == "ppt" else create_pdf(title, pitch)
    return jsonify({"download_link": f"/api/download/{os.path.basename(filename)}"})


@app.route("/api/download/<filename>")
def download_file(filename):
    return send_from_directory(
        os.path.abspath("generated_decks"), filename, as_attachment=True
    )


#history+stats
@app.route("/api/history", methods=["GET"])
@optional_auth
def history():
    if request.user_id:
        return jsonify({"history": get_user_pitches(request.user_id)})
    session_id = request.args.get("session_id", "anonymous")
    return jsonify({"history": get_pitch_history(session_id)})


@app.route("/api/history", methods=["POST"])
@optional_auth
def save():
    data = request.get_json()
    pitch_id = save_pitch(
        data.get("session_id", "anonymous"),
        data.get("title", ""),
        data.get("pitch", ""),
        data.get("style", "corporate"),
        data.get("grading", ""),
        request.user_id,
    )
    return jsonify({"id": pitch_id, "message": "Saved."})


@app.route("/api/history/<int:pitch_id>", methods=["GET"])
def get_pitch(pitch_id):
    pitch = get_pitch_by_id(pitch_id)
    if not pitch:
        return jsonify({"error": "Not found."}), 404
    return jsonify(pitch)


@app.route("/api/stats", methods=["GET"])
@auth_required
def stats():
    return jsonify(get_user_stats(request.user_id))


@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    return response


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
