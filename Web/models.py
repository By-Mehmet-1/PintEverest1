from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Yorum(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    icerik = db.Column(db.Text, nullable=False)
    kullanici_adi = db.Column(db.String(100), nullable=False)
    resim_id = db.Column(db.Integer, nullable=False)

