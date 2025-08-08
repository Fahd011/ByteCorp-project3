from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from backend.models.models import User
from backend.db import db
from datetime import datetime, timedelta

bp = Blueprint("auth", __name__)

@bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if not data.get("email") or not data.get("password"):
        return jsonify({"error": "Missing email or password"}), 400

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already exists"}), 400

    user = User(email=data["email"], password_hash=generate_password_hash(data["password"]))
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "User created"}), 201

@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data["email"]).first()
    if not user or not check_password_hash(user.password_hash, data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(identity=user.id)
    
    # Add 1 hour to current time for expiration
    expires_at = datetime.now() + timedelta(hours=1)
    
    return jsonify({
        "access_token": token,
        "expires_at": expires_at.isoformat(),
        "user": {
            "id": user.id,
            "email": user.email
        }
    }), 200
