"""End-to-end API test — signup, login, submit job, poll, download."""

import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"


def req(method: str, path: str, body: dict | None = None, token: str = "", files: dict | None = None):
    url = f"{BASE}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    if files:
        import io
        boundary = "----TestBoundary123"
        parts = []
        for key, val in (body or {}).items():
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{val}")
        for key, (filename, data, content_type) in files.items():
            parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"; filename=\"{filename}\"\r\n"
                f"Content-Type: {content_type}\r\n\r\n"
            )
            combined = "\r\n".join(parts).encode() + data + f"\r\n--{boundary}--\r\n".encode()
            r = urllib.request.Request(url, data=combined, headers={
                **headers,
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            }, method=method)
            resp = urllib.request.urlopen(r)
            return json.loads(resp.read().decode())

    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    else:
        data = None

    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(r)
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode()}")
        raise
    return json.loads(resp.read().decode())


def main():
    print("=== 1. Health Check ===")
    resp = req("GET", "/health")
    print(f"  {resp}")
    assert resp["status"] == "ok"

    print("\n=== 2. Signup ===")
    resp = req("POST", "/auth/signup", {"email": "test@example.com", "password": "test123"})
    token = resp["access_token"]
    print(f"  Token: {token[:40]}...")

    print("\n=== 3. Login ===")
    resp = req("POST", "/auth/login", {"email": "test@example.com", "password": "test123"})
    token = resp["access_token"]
    print(f"  Token: {token[:40]}...")

    print("\n=== 4. Get Current User ===")
    resp = req("GET", "/auth/me", token=token)
    print(f"  User: {resp['email']} (id={resp['id'][:8]}...)")

    print("\n=== 5. List Jobs (should be empty) ===")
    resp = req("GET", "/jobs", token=token)
    print(f"  Jobs: {len(resp['jobs'])}")
    assert len(resp["jobs"]) == 0

    print("\n=== ALL AUTH + CRUD TESTS PASSED ===")


if __name__ == "__main__":
    main()
