# app/routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import current_user, login_user, logout_user, login_required
from urllib.parse import urlparse as url_parse
from app import db
from app.models import User, Post, Friendship
from app.forms import LoginForm, RegistrationForm, PostForm
from flask import jsonify
import socket
import ipaddress
import subprocess
import platform
import time

bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/index')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.feed'))
    return render_template('base.html', title='Welcome')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.feed'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        # new users follow themselves so own posts show in feed easily
        user.follow(user)
        db.session.commit()
        flash('Registration successful. You can now log in.')
        return redirect(url_for('main.login'))
    return render_template('register.html', title='Register', form=form)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.feed'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('main.login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.feed')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(content=form.body.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post is now live.')
        return redirect(url_for('main.feed'))
    return render_template('create_post.html', title='Create Post', form=form)

@bp.route('/feed')
@login_required
def feed():
    # 1) posts from followed users (via friendship), latest first
    followed_posts = current_user.followed_posts().limit(50).all()

    # Always include the current user's own posts so they always see their posts
    own_posts = Post.query.filter_by(user_id=current_user.id).order_by(Post.timestamp.desc()).limit(50).all()

    # Merge and deduplicate by post id, keep order (own + followed, latest first)
    seen_ids = set()
    merged = []
    for p in (own_posts + followed_posts):
        if p.id not in seen_ids:
            seen_ids.add(p.id)
            merged.append(p)
    # Sort merged feed newest first
    merged.sort(key=lambda p: p.timestamp, reverse=True)
    feed_posts = merged[:50]

    # 2) recommendation: top users by follower count (excluding already followed)
    popular = User.query.outerjoin(User.friends_received).group_by(User.id).order_by(db.func.count(Friendship.user_id).desc()).limit(10).all()
    recommendations = [u for u in popular if u.id != current_user.id and not current_user.is_following(u)]

    # Show posts from recommendations if feed still short
    rec_posts = []
    if len(feed_posts) < 10:
        rec_user_ids = [u.id for u in recommendations[:5]]
        if rec_user_ids:
            rec_posts = Post.query.filter(Post.user_id.in_(rec_user_ids)).order_by(Post.timestamp.desc()).limit(20).all()

    # Final feed: own/followed posts then recommendation posts (no duplicates)
    final_feed = feed_posts + [p for p in rec_posts if p.id not in seen_ids]
    return render_template('feed.html', title='Your Feed', posts=final_feed, recommendations=recommendations[:5])

@bp.route('/user/<username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(user_id=user.id).order_by(Post.timestamp.desc()).all()
    is_following = current_user.is_following(user)
    return render_template('profile.html', user=user, posts=posts, is_following=is_following)

@bp.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    if username == current_user.username:
        flash('You cannot follow yourself.')
        return redirect(url_for('main.profile', username=username))
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User not found.')
        return redirect(url_for('main.feed'))
    current_user.follow(user)
    db.session.commit()
    flash(f'You are now following {username}.')
    return redirect(url_for('main.profile', username=username))

@bp.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User not found.')
        return redirect(url_for('main.feed'))
    if user == current_user:
        flash('You cannot unfollow yourself.')
        return redirect(url_for('main.profile', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash(f'You have unfollowed {username}.')
    return redirect(url_for('main.profile', username=username))

@bp.route('/_health')
def health():
    return jsonify({"status":"ok"}), 200

@bp.route('/whoami')
def whoami():
    return jsonify({"host": socket.gethostname()}), 200

# ─────────────────────────────────────────
#  NETWORK LAB — Page & API Endpoints
# ─────────────────────────────────────────

@bp.route('/network-lab')
@login_required
def network_lab():
    """Network Lab dashboard page."""
    return render_template('network_lab.html', title='Network Lab')


@bp.route('/api/network/http-headers')
@login_required
def api_http_headers():
    """Return the HTTP request headers of the current request with explanations."""
    explanations = {
        'Host': 'Identifies the server domain name and port the client wants to connect to (HTTP/1.1 required).',
        'User-Agent': 'Identifies the client browser, OS, and rendering engine making the request.',
        'Accept': 'Tells the server what MIME types the client can handle in the response.',
        'Accept-Encoding': 'Lists compression algorithms the client supports (gzip, br, deflate).',
        'Accept-Language': 'Client\'s preferred natural language for the response.',
        'Connection': 'Controls whether the TCP connection stays open after the response (keep-alive = persistent).',
        'Cookie': 'HTTP state management — carries the session token and other client-side state back to the server.',
        'Referer': 'The URL of the previous page that linked to this request.',
        'Cache-Control': 'Directives for caching mechanisms in both requests and responses.',
        'Upgrade-Insecure-Requests': 'Client signals it prefers HTTPS over HTTP.',
        'Sec-Fetch-Site': 'Indicates the relationship between origin and request (same-origin, cross-site).',
        'Sec-Fetch-Mode': 'Indicates the mode of the request (navigate, no-cors, cors).',
        'Sec-Fetch-Dest': 'Indicates the destination of the request (document, image, script).',
        'X-Forwarded-For': 'Added by Nginx proxy — shows the real client IP address.',
        'X-Real-IP': 'Added by Nginx — the original client IP before proxying.',
    }
    headers_list = []
    for key, value in request.headers:
        # Mask session cookie value for security
        if key.lower() == 'cookie':
            value = value[:30] + '...[masked]' if len(value) > 30 else value
        headers_list.append({
            'name': key,
            'value': value,
            'explanation': explanations.get(key, 'Standard HTTP header carrying metadata about the request/response.')
        })
    return jsonify({
        'method': request.method,
        'url': request.url,
        'http_version': 'HTTP/1.1',
        'remote_addr': request.remote_addr,
        'headers': headers_list,
        'header_count': len(headers_list)
    })


@bp.route('/api/network/dns-lookup', methods=['POST'])
@login_required
def api_dns_lookup():
    """Real DNS resolution using Python's socket module."""
    data = request.get_json() or {}
    hostname = data.get('hostname', '').strip()
    if not hostname:
        return jsonify({'error': 'Hostname is required'}), 400
    if len(hostname) > 255:
        return jsonify({'error': 'Hostname too long'}), 400

    results = []
    start = time.time()
    try:
        # A/AAAA records via getaddrinfo
        addr_infos = socket.getaddrinfo(hostname, None)
        seen = set()
        for info in addr_infos:
            ip = info[4][0]
            family = 'IPv4 (A record)' if info[0] == socket.AF_INET else 'IPv6 (AAAA record)'
            if ip not in seen:
                seen.add(ip)
                results.append({'type': family, 'address': ip})
        # Reverse DNS on first result
        reverse = None
        if results:
            try:
                reverse = socket.gethostbyaddr(results[0]['address'])[0]
            except Exception:
                reverse = 'No reverse DNS entry'
        elapsed = round((time.time() - start) * 1000, 2)
        return jsonify({
            'hostname': hostname,
            'records': results,
            'reverse_dns': reverse,
            'query_time_ms': elapsed,
            'server': 'System DNS Resolver',
            'success': True
        })
    except socket.gaierror as e:
        return jsonify({'hostname': hostname, 'error': str(e), 'success': False})


@bp.route('/api/network/cidr-calculator', methods=['POST'])
@login_required
def api_cidr_calculator():
    """Real CIDR subnet calculator using Python's ipaddress module."""
    data = request.get_json() or {}
    cidr = data.get('cidr', '').strip()
    if not cidr:
        return jsonify({'error': 'CIDR notation required (e.g. 192.168.1.0/24)'}), 400
    try:
        net = ipaddress.ip_network(cidr, strict=False)
        hosts = list(net.hosts())
        first_host = str(hosts[0]) if hosts else str(net.network_address)
        last_host  = str(hosts[-1]) if hosts else str(net.broadcast_address)
        # Binary representation
        na = int(net.network_address)
        mask = int(net.netmask)
        def to_binary_dotted(n):
            return '.'.join(f'{(n >> (24 - 8*i)) & 0xFF:08b}' for i in range(4))
        return jsonify({
            'input': cidr,
            'network_address': str(net.network_address),
            'broadcast_address': str(net.broadcast_address),
            'netmask': str(net.netmask),
            'wildcard_mask': str(net.hostmask),
            'prefix_length': net.prefixlen,
            'total_addresses': net.num_addresses,
            'usable_hosts': max(0, net.num_addresses - 2),
            'first_host': first_host,
            'last_host': last_host,
            'ip_class': 'A' if net.prefixlen <= 8 else ('B' if net.prefixlen <= 16 else 'C'),
            'is_private': net.is_private,
            'binary_network': to_binary_dotted(na),
            'binary_netmask': to_binary_dotted(mask),
            'success': True
        })
    except ValueError as e:
        return jsonify({'error': str(e), 'success': False})


@bp.route('/api/network/simulate-load-balancer', methods=['POST'])
@login_required
def api_simulate_load_balancer():
    """Simulate Nginx load balancing algorithms in Python."""
    data = request.get_json() or {}
    algorithm = data.get('algorithm', 'round_robin')
    num_requests = min(int(data.get('requests', 10)), 30)
    servers = [
        {'name': 'webapp1', 'ip': '172.20.0.2', 'port': 5000, 'weight': 1, 'connections': 0},
        {'name': 'webapp2', 'ip': '172.20.0.3', 'port': 5000, 'weight': 2, 'connections': 0},
    ]
    distribution = []
    rr_index = 0

    for i in range(num_requests):
        client_ip = f'10.0.0.{(i * 7 + 13) % 254 + 1}'
        if algorithm == 'round_robin':
            server = servers[rr_index % len(servers)]
            rr_index += 1
            reason = f'Request #{i+1} → server index {(rr_index-1) % len(servers)}'
        elif algorithm == 'ip_hash':
            h = sum(ord(c) for c in client_ip) % len(servers)
            server = servers[h]
            reason = f'hash({client_ip}) = {h} → always routes same IP to same server'
        elif algorithm == 'weighted':
            # Weighted round-robin: webapp2 gets 2x requests
            cycle_pos = i % (sum(s['weight'] for s in servers))
            cumulative = 0
            server = servers[-1]
            for s in servers:
                cumulative += s['weight']
                if cycle_pos < cumulative:
                    server = s
                    break
            reason = f'Weight position {cycle_pos} → {server["name"]} (weight={server["weight"]})'
        else:
            server = servers[0]
            reason = 'Default'

        server['connections'] += 1
        response_time = 12 + (server['connections'] % 5) * 3
        distribution.append({
            'request_num': i + 1,
            'client_ip': client_ip,
            'server': server['name'],
            'server_ip': server['ip'],
            'response_time_ms': response_time,
            'status': 200,
            'reason': reason
        })

    summary = {s['name']: s['connections'] for s in servers}
    return jsonify({
        'algorithm': algorithm,
        'total_requests': num_requests,
        'servers': [{'name': s['name'], 'ip': s['ip'], 'port': s['port'],
                     'requests_served': s['connections']} for s in servers],
        'distribution': distribution,
        'summary': summary,
        'success': True
    })


@bp.route('/api/network/ping', methods=['POST'])
@login_required
def api_ping():
    """Run real OS ping and parse output."""
    data = request.get_json() or {}
    host = data.get('host', '').strip()
    if not host:
        return jsonify({'error': 'Host is required'}), 400
    # Safety: only allow valid hostnames/IPs
    allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_')
    if not all(c in allowed_chars for c in host) or len(host) > 253:
        return jsonify({'error': 'Invalid hostname'}), 400

    try:
        is_win = platform.system().lower() == 'windows'
        count_flag = '-n' if is_win else '-c'
        cmd = ['ping', count_flag, '4', host]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        output = result.stdout or result.stderr
        lines = [l for l in output.splitlines() if l.strip()]
        return jsonify({
            'host': host,
            'raw_output': output,
            'lines': lines,
            'exit_code': result.returncode,
            'success': result.returncode == 0,
            'reachable': result.returncode == 0
        })
    except subprocess.TimeoutExpired:
        return jsonify({'host': host, 'error': 'Ping timed out (15s)', 'success': False})
    except Exception as e:
        return jsonify({'host': host, 'error': str(e), 'success': False})
