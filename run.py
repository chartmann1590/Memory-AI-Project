# run.py

from app import create_app, db
from app.models import User
from flask import render_template

app = create_app()

# Instead of using the before_first_request decorator,
# create the tables explicitly within the app context.
with app.app_context():
    db.create_all()

# A simple main route example.
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
