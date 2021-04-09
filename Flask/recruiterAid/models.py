from datetime import datetime
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from sqlalchemy import ForeignKey

from recruiterAid import db, login_manager, app
from flask_login import UserMixin



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    __tablename__ = 'parent'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"


class FileContents(db.Model):
    __tablename__ = 'child'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey('parent.id'))
    resume_name = db.Column(db.String(500))
    resume_file = db.Column(db.LargeBinary)


# class RankingPolicy(db.Model):
#     __tablename__ = 'policy'
#     id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column(db.Integer, ForeignKey('parent.id'))
#     rank_policy = db.Column(db.String(500))


class RankingPolicy(db.Model):
    __tablename__ = 'policy'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey('parent.id'))
    # rank_policy = db.Column(db.String(500))
    experience = db.Column(db.String(100))
    skill = db.Column(db.String(300))
    degree = db.Column(db.String(400))
    publication = db.Column(db.String(100))
    patent = db.Column(db.String(100))
