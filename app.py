from flask import Flask, render_template, request, redirect, url_for, jsonify #flask allows us to create an app#
from flask_sqlalchemy import SQLAlchemy
import sys

app = Flask(__name__) #create an app with the name of our file ie app#
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://diegoalmada@localhost:5432/pp'
t #links sqlalchemy to our flask app#

class Todo(db.Model): #to link it to sqlalchemy this needs to inherit from db.Model#
    __tablename__ = 'todos'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(), nullable=False)

    def __repr__(self):
        return f'<Todo {self.id} {self.description}>'

db.create_all() #to sync our models to the database#

@app.route('/todos/create', methods=['POST'])
def create_todo():
    error = False
    try:
        description = request.get_json()['description']
        todo = Todo(description=description)
        db.session.add(todo)
        db.session.commit() #**#
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if not error:
        return jsonify({
            'description': todo.description #if db = SQLAlchemy(app) does not define expire_on_commit: then todo.description would be expired by now **#
        })



@app.route('/') #this route listens to our homepage#
def index(): #we'll call our route handler: index#
    return render_template('index.html', data=Todo.query.all()
    )#we want this to return an HTML template, instead of a string, we do that with the model render_template this will make an HTML file to render to the user whenever our user visits this route#
    #by default flask looks for your templates in a folder called templated in your project directory todoapp, so lets create one#
