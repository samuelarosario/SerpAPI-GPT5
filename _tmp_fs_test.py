import requests, json, sys, time
base='http://127.0.0.1:8000'
creds={'email':'admin@local','password':'admin'}
try:
    login = requests.post(base+'/auth/login', json=creds, timeout=15)
except Exception as e:
    print('Login request exception', e); sys.exit(1)
print('LOGIN STATUS', login.status_code)
if login.status_code!=200:
    print('Login failed body:', login.text)
    sys.exit(1)
acc = login.json().get('access_token')
print('Access token present?', bool(acc))
headers={'Authorization':'Bearer '+acc}
params={'origin':'JFK','destination':'LAX','date':'2025-12-15'}
search = requests.get(base+'/api/flight_search', params=params, headers=headers, timeout=60)
print('SEARCH STATUS', search.status_code)
print('SEARCH URL', search.url)
print('SEARCH BODY (trunc):', search.text[:500])
