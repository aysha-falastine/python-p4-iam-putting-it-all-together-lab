#!/usr/bin/env python3

from flask import request, session, make_response, jsonify
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError

from config import app, db, api, bcrypt

# Import models after db is initialized so their metadata is available to
# SQLAlchemy before creating tables. Tests and the app expect the DB tables
# to exist when the test harness runs, so create them here once models are
# imported/registered.
from models import User, Recipe

# Ensure tables exist for the tests and app runtime. Using create_all here
# guarantees the tables are created with the current model definitions.
with app.app_context():
    db.create_all()


# ------------------ Resources ------------------

class Signup(Resource):
    def post(self):
        data = request.get_json()
        try:
            # Construct user without password then set via the write-only
            # property so our model's setter runs (hashing, validation).
            user = User(
                username=data['username'],
                image_url=data.get('image_url', ''),
                bio=data.get('bio', '')
            )
            user.password = data['password']
            db.session.add(user)
            db.session.commit()
            session['user_id'] = user.id
            return make_response(user.to_dict(), 201)
        except IntegrityError:
            db.session.rollback()
            return make_response({"errors": ["Username must be unique."]}, 422)
        except Exception as e:
            db.session.rollback()
            return make_response({"errors": [str(e)]}, 422)


class CheckSession(Resource):
    def get(self):
        user_id = session.get('user_id')
        if user_id:
            user = User.query.get(user_id)
            if user:
                return make_response(user.to_dict(), 200)
        return make_response({"error": "Unauthorized"}, 401)


class Login(Resource):
    def post(self):
        data = request.get_json()
        user = User.query.filter_by(username=data.get('username')).first()
        if user and user.check_password(data.get('password')):
            session['user_id'] = user.id
            return make_response(user.to_dict(), 200)
        return make_response({"error": "Invalid username or password"}, 401)


class Logout(Resource):
    def delete(self):
        # Tests set `session['user_id'] = None` to simulate no session, so
        # check for a truthy user_id rather than key presence.
        if session.get('user_id'):
            session.pop('user_id')
            return "", 204
        return make_response({"error": "Unauthorized"}, 401)


class RecipeIndex(Resource):
    def get(self):
        # Treat a falsy user_id (None) as unauthorized
        if not session.get('user_id'):
            return make_response({"error": "Unauthorized"}, 401)
        # Only return recipes belonging to the logged-in user
        recipes = [r.to_dict() for r in Recipe.query.filter_by(user_id=session['user_id']).all()]
        return make_response(jsonify(recipes), 200)

    def post(self):
        if 'user_id' not in session:
            return make_response({"error": "Unauthorized"}, 401)
        data = request.get_json()
        user = User.query.get(session['user_id'])
        try:
            recipe = Recipe(
                title=data['title'],
                instructions=data['instructions'],
                minutes_to_complete=data.get('minutes_to_complete', 0),
                user=user
            )
            db.session.add(recipe)
            db.session.commit()
            return make_response(recipe.to_dict(), 201)
        except Exception as e:
            db.session.rollback()
            return make_response({"errors": [str(e)]}, 422)


# ------------------ Routes ------------------
api.add_resource(Signup, '/signup', endpoint='signup')
api.add_resource(CheckSession, '/check_session', endpoint='check_session')
api.add_resource(Login, '/login', endpoint='login')
api.add_resource(Logout, '/logout', endpoint='logout')
api.add_resource(RecipeIndex, '/recipes', endpoint='recipes')


# ------------------ Run App ------------------
if __name__ == '__main__':
    app.run(port=5555, debug=True)
