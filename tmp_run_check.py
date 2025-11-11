import json
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:8080"


def _log(prefix: str, url: str, status: int, body: str) -> None:
    print(f"[{prefix}] {url} -> {status} | {body}")


def _request(method: str, url: str, payload=None, headers=None, timeout: int = 5):
    body_bytes = None
    req_headers = headers.copy() if headers else {}
    if payload is not None:
        body_bytes = json.dumps(payload).encode()
        req_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=body_bytes, method=method, headers=req_headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read().decode()
            _log(method, url, response.status, text)
            return response.status, text
    except urllib.error.HTTPError as err:
        detail = err.read().decode()
        print(f"[{method} ERRO]", url, err.code, detail)
    except Exception as exc:  # noqa: BLE001
        print(f"[{method} ERRO]", url, str(exc))
    return None, None


def get(url: str, headers=None):
    return _request("GET", url, headers=headers, timeout=3)


def post(url: str, payload, headers=None):
    return _request("POST", url, payload=payload, headers=headers)


# Health
get(BASE_URL + "/health")

# Login
status, response_body = post(BASE_URL + "/login", {"email": "alice@example.com", "password": "password123"})
if status == 200 and response_body:
    token = json.loads(response_body)["token"]
    # Status com token
    get(BASE_URL + "/user/1/status", headers={"Authorization": f"Bearer {token}"})
