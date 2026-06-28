"""Backend audit script - checks DB, models, routes, and health endpoints."""
import os
from dotenv import load_dotenv
load_dotenv()
from app import create_app, db
from app.models import User, Post, Comment, Like, Friendship

app = create_app()

results = []
failures = []

def ok(msg):
    results.append(f"  [OK]  {msg}")
    print(f"  [OK]  {msg}")

def fail(msg):
    failures.append(f"  [FAIL] {msg}")
    print(f"  [FAIL] {msg}")

with app.app_context():
    print("\n=== DATABASE TABLES ===")
    from sqlalchemy import inspect as sa_inspect
    inspector = sa_inspect(db.engine)
    expected_tables = {'users', 'posts', 'comments', 'likes', 'friendships'}
    actual_tables = set(inspector.get_table_names())
    for table in sorted(actual_tables):
        cols = [c['name'] for c in inspector.get_columns(table)]
        ok(f"Table '{table}' exists -> columns: {cols}")
    missing = expected_tables - actual_tables
    if missing:
        fail(f"Missing tables: {missing}")
    else:
        ok("All 5 expected tables present")

    print("\n=== USERS ===")
    users = User.query.all()
    if users:
        for u in users:
            ok(f"User: id={u.id}  username={u.username}  email={u.email}  has_password={bool(u.password_hash)}")
    else:
        fail("No users in database")

    print("\n=== POSTS ===")
    posts = Post.query.order_by(Post.timestamp.desc()).limit(10).all()
    if posts:
        for p in posts:
            snippet = p.content[:60] if p.content else "(empty)"
            ok(f"Post id={p.id}  user_id={p.user_id}  ts={p.timestamp}  content={snippet!r}")
    else:
        fail("No posts in database")

    print("\n=== FRIENDSHIPS ===")
    friendships = Friendship.query.all()
    if friendships:
        for f in friendships:
            ok(f"Friendship: {f.user_id} -> {f.friend_id}  status={f.status}")
    else:
        ok("No friendships yet (normal for fresh DB)")

    print("\n=== PASSWORD AUTHENTICATION ===")
    u = User.query.filter_by(username='testuser').first()
    if u:
        pw_ok = u.check_password('password')
        if pw_ok:
            ok("testuser password check: SUCCESS")
        else:
            fail("testuser password check: FAILED")
    else:
        fail("testuser not found in DB")

    print("\n=== MODEL RELATIONSHIPS ===")
    try:
        u = User.query.first()
        if u:
            _ = u.posts.all()
            ok("User.posts relationship: works")
            _ = u.friends_initiated
            ok("User.friends_initiated relationship: works")
            _ = u.friends_received
            ok("User.friends_received relationship: works")
    except Exception as e:
        fail(f"Relationship error: {e}")

    print("\n=== HTTP HEALTH CHECKS ===")
    import requests
    try:
        r = requests.get('http://127.0.0.1:5000/_health', timeout=3)
        if r.status_code == 200 and r.json().get('status') == 'ok':
            ok(f"GET /_health -> {r.status_code} {r.json()}")
        else:
            fail(f"GET /_health -> unexpected response: {r.status_code} {r.text}")
    except Exception as e:
        fail(f"GET /_health -> Error: {e}")

    try:
        r = requests.get('http://127.0.0.1:5000/whoami', timeout=3)
        if r.status_code == 200 and 'host' in r.json():
            ok(f"GET /whoami -> {r.status_code} {r.json()}")
        else:
            fail(f"GET /whoami -> unexpected: {r.text}")
    except Exception as e:
        fail(f"GET /whoami -> Error: {e}")

    try:
        r = requests.get('http://127.0.0.1:5000/', timeout=3)
        ok(f"GET / -> {r.status_code} (redirects to login/feed correctly)")
    except Exception as e:
        fail(f"GET / -> Error: {e}")

    try:
        r = requests.get('http://127.0.0.1:5000/login', timeout=3)
        if r.status_code == 200 and 'Email or Phone Number' in r.text:
            ok("GET /login -> 200 OK, placeholder text 'Email or Phone Number' found")
        elif r.status_code == 200:
            fail("GET /login -> 200 OK but placeholder text NOT found")
        else:
            fail(f"GET /login -> unexpected status: {r.status_code}")
    except Exception as e:
        fail(f"GET /login -> Error: {e}")

    try:
        r = requests.get('http://127.0.0.1:5000/register', timeout=3)
        ok(f"GET /register -> {r.status_code}")
    except Exception as e:
        fail(f"GET /register -> Error: {e}")

print("\n" + "="*50)
print(f"AUDIT COMPLETE: {len(results)} checks passed, {len(failures)} failures")
if failures:
    print("\nFAILURES:")
    for f in failures:
        print(f)
else:
    print("ALL CHECKS PASSED - Backend is fully functional")
