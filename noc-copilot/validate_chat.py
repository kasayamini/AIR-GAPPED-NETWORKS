import requests

base = 'http://127.0.0.1:8001'
url = base + '/api/chat'
payload = {
    'question': 'What is the most likely cause of a bandwidth spike with packet loss, and what should the operator check first?'
}
print('POST', url)
try:
    with requests.post(url, json=payload, timeout=(5, 120), stream=True) as resp:
        print('status', resp.status_code)
        print('headers', resp.headers)
        for i, line in enumerate(resp.iter_lines(decode_unicode=True)):
            if not line:
                continue
            print('LINE', i, repr(line))
            if i >= 20:
                break
        print('done reading')
except Exception as exc:
    print('EXCEPTION', repr(exc))
