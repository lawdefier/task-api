import urllib.request, json

def req(method, url, data=None):
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(
        url, data=body, method=method,
        headers={'Content-Type': 'application/json'} if body else {}
    )
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, resp.read().decode()
    except Exception as e:
        return getattr(e, 'code', '?'), getattr(e, 'read', lambda: b'')().decode()

base = 'http://localhost:8000'
checks = [
    ('GET',    '/',         None,                                    200),
    ('GET',    '/health',   None,                                    200),
    ('GET',    '/tasks',    None,                                    200),
    ('GET',    '/tasks/1',  None,                                    200),
    ('GET',    '/tasks/99', None,                                    404),
    ('POST',   '/tasks',    {'title': 'Buy milk'},                   201),
    ('POST',   '/tasks',    {},                                      422),
    ('PUT',    '/tasks/1',  {'title': 'Done reading', 'done': True}, 200),
    ('DELETE', '/tasks/2',  None,                                    204),
    ('GET',    '/stats',    None,                                    200),
]

print(f"{'Method':<8} {'Path':<20} {'Expect':<8} {'Got':<8} Pass?")
print('-' * 60)
all_pass = True
for method, path, data, expect in checks:
    status, body = req(method, base + path, data)
    ok = (status == expect)
    if not ok:
        all_pass = False
    mark = 'PASS' if ok else 'FAIL'
    snippet = (body[:55].replace('\n', '') if body else '(empty)')
    print(f"{method:<8} {path:<20} {expect:<8} {status:<8} {mark}  {snippet}")

print()
print('All checks passed!' if all_pass else 'SOME CHECKS FAILED -- see above')
