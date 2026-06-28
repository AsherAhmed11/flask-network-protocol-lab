from dotenv import load_dotenv
load_dotenv()
from app import create_app, db
from app.models import User

app = create_app()

def test_login():
    with app.app_context():
        print("Checking users...")
        users = User.query.all()
        for u in users:
            print(f"User: {u.username}, Email: {u.email}")
            
        username = "testuser" # Or whatever the user registered with
        user = User.query.filter_by(username=username).first()
        if user:
            print(f"Found user: {user.username}")
            # Test password (assuming 'password' for testuser)
            if user.check_password('password'):
                print("Password check: SUCCESS")
            else:
                print("Password check: FAILED")
        else:
            print(f"User {username} not found.")

if __name__ == "__main__":
    test_login()
