# app/models.py
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    bio = db.Column(db.Text)
    profile_pic = db.Column(db.String(255))
    posts = db.relationship('Post', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)
    likes = db.relationship('Like', backref='user', lazy=True)

    # Friendships
    friends_initiated = db.relationship('Friendship', foreign_keys='Friendship.user_id', backref='user', lazy=True)
    friends_received = db.relationship('Friendship', foreign_keys='Friendship.friend_id', backref='friend', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

    def follow(self, user):
        if not self.is_following(user):
            f = Friendship(user_id=self.id, friend_id=user.id, status='accepted')
            db.session.add(f)

    def unfollow(self, user):
        f = Friendship.query.filter_by(user_id=self.id, friend_id=user.id).first()
        if f:
            db.session.delete(f)

    def is_following(self, user):
        return Friendship.query.filter_by(user_id=self.id, friend_id=user.id).count() > 0

    def followed_posts(self):
        return Post.query.join(
            Friendship, (Friendship.friend_id == Post.user_id)
        ).filter(
            Friendship.user_id == self.id
        ).order_by(Post.timestamp.desc())

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    comments = db.relationship('Comment', backref='post', lazy=True)
    likes = db.relationship('Like', backref='post', lazy=True)

    def __repr__(self):
        return f'<Post {self.id}>'

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Like(db.Model):
    __tablename__ = 'likes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Friendship(db.Model):
    __tablename__ = 'friendships'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    friend_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    status = db.Column(db.String(20), default='pending') # pending, accepted, blocked
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
