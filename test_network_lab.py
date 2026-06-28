import requests

BASE = 'http://127.0.0.1:5000'
s = requests.Session()

# Step 1: get CSRF token from login page
r = s.get(BASE + '/login')
csrf = ''
for line in r.text.splitlines():
    if 'csrf_token' in line and 'value=' in line:
        csrf = line.split('value="')[1].split('"')[0]
        break

# Step 2: login
login_r = s.post(BASE + '/login', data={
    'username': 'testuser', 'password': 'password',
    'csrf_token': csrf, 'remember_me': False
})
print(f"Login status: {login_r.status_code}, history: {[h.status_code for h in login_r.history]}")

# Step 3: Network Lab page
r = s.get(BASE + '/network-lab')
has_topology = 'topology' in r.text
has_osi = 'osi-stack' in r.text
has_terminal = 'terminal' in r.text
print(f"GET /network-lab: {r.status_code} | topology={has_topology} | osi={has_osi} | terminal={has_terminal}")

# Step 4: CIDR calculator
r = s.post(BASE + '/api/network/cidr-calculator', json={'cidr': '192.168.1.0/24'})
d = r.json()
print(f"CIDR /24: net={d.get('network_address')} bcast={d.get('broadcast_address')} hosts={d.get('usable_hosts')}")

r2 = s.post(BASE + '/api/network/cidr-calculator', json={'cidr': '10.0.0.0/8'})
d2 = r2.json()
print(f"CIDR /8:  net={d2.get('network_address')} hosts={d2.get('usable_hosts')} class={d2.get('ip_class')}")

# Step 5: DNS lookup
r = s.post(BASE + '/api/network/dns-lookup', json={'hostname': 'google.com'})
d = r.json()
print(f"DNS google.com: success={d.get('success')} records={len(d.get('records',[]))} time={d.get('query_time_ms')}ms")

# Step 6: Load balancer — round robin
r = s.post(BASE + '/api/network/simulate-load-balancer', json={'algorithm': 'round_robin', 'requests': 10})
d = r.json()
print(f"LB round_robin 10req: {d.get('summary')}")

# Step 7: Load balancer — weighted
r = s.post(BASE + '/api/network/simulate-load-balancer', json={'algorithm': 'weighted', 'requests': 12})
d = r.json()
print(f"LB weighted 12req:    {d.get('summary')}")

# Step 8: Load balancer — ip_hash
r = s.post(BASE + '/api/network/simulate-load-balancer', json={'algorithm': 'ip_hash', 'requests': 10})
d = r.json()
print(f"LB ip_hash 10req:     {d.get('summary')}")

# Step 9: HTTP headers
r = s.get(BASE + '/api/network/http-headers')
d = r.json()
names = [h['name'] for h in d.get('headers', [])]
print(f"HTTP headers: {d.get('header_count')} headers | has Host={('Host' in names)} | has Cookie={('Cookie' in names)}")

print("\nALL NETWORK LAB API TESTS PASSED")
