from dotenv import load_dotenv
load_dotenv()

from app import create_app, db
from app.models import User, Post

app = create_app()

# if __name__ == '__main__':
    # create DB tables if missing
with app.app_context():
    db.create_all()
# app.run(debug=True)
