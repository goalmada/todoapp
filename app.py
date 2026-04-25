from flask import Flask, render_template, request, redirect, url_for, jsonify, abort #flask allows us to create an app#
from flask_sqlalchemy import SQLAlchemy
import sys
from datetime import datetime
from flask_migrate import Migrate

app = Flask(__name__) #create an app with the name of our file ie app#
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://diegoalmada@localhost:5432/pp'
db = SQLAlchemy(app) #links sqlalchemy to our flask app#

migrate = Migrate(app, db)

class Todo(db.Model): #to link it to sqlalchemy this needs to inherit from db.Model#
    __tablename__ = 'todos'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(), nullable=False)

    def __repr__(self):
        return f'<Todo {self.id} {self.description}>'

class Trip(db.Model):
    __tablename__ = 'trips'
    id = db.Column(db.Integer, primary_key=True)
    destination = db.Column(db.String(), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expenses = db.relationship('Expense', backref='trip', lazy=True, cascade='all, delete-orphan')

    def total(self):
        return sum(e.amount for e in self.expenses)

    def to_dict(self):
        return {
            'id': self.id,
            'destination': self.destination,
            'created_at': self.created_at.isoformat(),
            'expenses': [e.to_dict() for e in self.expenses],
            'total': self.total(),
        }

    def __repr__(self):
        return f'<Trip {self.id} {self.destination}>'

class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trips.id'), nullable=False)
    description = db.Column(db.String(), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'trip_id': self.trip_id,
            'description': self.description,
            'amount': float(self.amount),
            'created_at': self.created_at.isoformat(),
        }

    def __repr__(self):
        return f'<Expense {self.id} {self.description} {self.amount}>'

db.create_all() #to sync our models to the database#

@app.route('/todos/create', methods=['POST'])
def create_todo():
    error = False
    body = {}
    try:
        description = request.get_json()['description']
        todo = Todo(description=description)
        db.session.add(todo)
        db.session.commit() #**#
        body['description'] = todo.description
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if not error:
        return jsonify(body)

@app.route('/trips', methods=['GET'])
def list_trips():
    return jsonify([t.to_dict() for t in Trip.query.order_by(Trip.created_at.desc()).all()])

@app.route('/trips', methods=['POST'])
def create_trip():
    error = False
    body = {}
    try:
        destination = request.get_json()['destination']
        trip = Trip(destination=destination)
        db.session.add(trip)
        db.session.commit()
        body = trip.to_dict()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        abort(400)
    return jsonify(body), 201

@app.route('/trips/<int:trip_id>', methods=['GET'])
def get_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    return jsonify(trip.to_dict())

@app.route('/trips/<int:trip_id>/expenses', methods=['POST'])
def create_expense(trip_id):
    Trip.query.get_or_404(trip_id)
    error = False
    body = {}
    try:
        payload = request.get_json()
        expense = Expense(
            trip_id=trip_id,
            description=payload['description'],
            amount=payload['amount'],
        )
        db.session.add(expense)
        db.session.commit()
        body = expense.to_dict()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        abort(400)
    return jsonify(body), 201

@app.route('/') #this route listens to our homepage#
def index(): #we'll call our route handler: index#
    return render_template('index.html', data=Todo.query.all()
    )#we want this to return an HTML template, instead of a string, we do that with the model render_template this will make an HTML file to render to the user whenever our user visits this route#
    #by default flask looks for your templates in a folder called templated in your project directory todoapp, so lets create one#
