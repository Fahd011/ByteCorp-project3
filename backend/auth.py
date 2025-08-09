from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from models.models import User

def get_current_user():
    verify_jwt_in_request()
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return user
