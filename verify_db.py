import time
from dotenv import load_dotenv
load_dotenv()
from app import create_app, db
from app.models import User, Post

app = create_app()

def verify_db():
    with app.app_context():
        print("Waiting for database to be ready...")
        # Simple retry logic
        for i in range(10):
            try:
                db.drop_all()
                db.create_all()
                print("Tables created successfully.")
                break
            except Exception as e:
                print(f"Database not ready yet: {e}")
                time.sleep(2)
        else:
            print("Failed to connect to database.")
            return

        # Create a dummy user
        if not User.query.filter_by(username='testuser').first():
            user = User(username='testuser', email='test@example.com')
            user.set_password('password')
            db.session.add(user)
            db.session.commit()
            print("Dummy user created.")
        else:
            print("Dummy user already exists.")

        # Verify user
        user = User.query.filter_by(username='testuser').first()
        if user:
            print(f"Verified user: {user.username}")
        
        print("Database verification complete.")

if __name__ == "__main__":
    verify_db()
