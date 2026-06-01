from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

with app.app_context():
    db.create_all()

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    fn = data.get('first_name', '')
    ln = data.get('last_name', '')
    em = data.get('email', '')
    pw = data.get('password', '')

    if not (1 <= len(fn) <= 50):
        return jsonify({"error": "Invalid first name"}), 400
    if not (1 <= len(ln) <= 50):
        return jsonify({"error": "Invalid last name"}), 400
    if not (1 <= len(em) <= 20):
        return jsonify({"error": "Invalid email"}), 400
    if not (10 <= len(pw) <= 100):
        return jsonify({"error": "Invalid password"}), 400

    new_user = User(first_name=fn, last_name=ln, email=em, password=pw)
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "User created"}), 201
    except:
        return jsonify({"error": "Email already exists"}), 400

if __name__ == '__main__':
    app.run(debug=True)