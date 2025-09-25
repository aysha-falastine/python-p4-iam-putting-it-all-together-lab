from sqlalchemy.orm import validates
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy_serializer import SerializerMixin
from config import db, bcrypt  # make sure bcrypt is initialized in config


class User(db.Model, SerializerMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    # Allow a nullable password hash so tests can create users without setting
    # a password in some cases. Validation and hashing are still provided by
    # the write-only properties.
    _password_hash = db.Column(db.String, nullable=True)
    image_url = db.Column(db.String, default="")
    bio = db.Column(db.String, default="")

    recipes = db.relationship('Recipe', back_populates='user', cascade='all, delete-orphan')

    serialize_rules = ('-recipes.user',)

    @hybrid_property
    def password(self):
        raise AttributeError("Password is write-only.")

    @password.setter
    def password(self, plaintext):
        if not plaintext:
            raise ValueError("Password cannot be empty.")
        self._password_hash = bcrypt.generate_password_hash(plaintext).decode('utf-8')

    # Tests expect a write-only `password_hash` attribute to be settable and
    # raise on access. Provide that interface (mapped column is `_password_hash`).
    @hybrid_property
    def password_hash(self):
        raise AttributeError("Password hash is write-only.")

    @password_hash.setter
    def password_hash(self, plaintext):
        if not plaintext:
            raise ValueError("Password cannot be empty.")
        self._password_hash = bcrypt.generate_password_hash(plaintext).decode('utf-8')

    def check_password(self, plaintext):
        if not self._password_hash:
            return False
        return bcrypt.check_password_hash(self._password_hash, plaintext)

    # Tests (and some calling code) expect an `authenticate` method name.
    def authenticate(self, plaintext):
        return self.check_password(plaintext)


class Recipe(db.Model, SerializerMixin):
    __tablename__ = 'recipes'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    instructions = db.Column(db.String, nullable=False)
    minutes_to_complete = db.Column(db.Integer, default=0)

    # Allow user_id to be nullable so recipes can be created without assigning
    # a user in some tests (they assert recipe attributes without an associated
    # user). Relationship still exists when set.
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user = db.relationship('User', back_populates='recipes')

    serialize_rules = ('-user.recipes',)

    @validates('instructions')
    def validate_instructions(self, key, instructions):
        if not instructions or len(instructions.strip()) < 50:
            raise ValueError("Instructions must be at least 50 characters long.")
        return instructions
