"""Typed-light HTTP facade: explicit status checks belong in the tests."""
from __future__ import annotations
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from framework.config import BASE_URL, API_TIMEOUT

class BookStoreAPI:
    def __init__(self):
        self.session = requests.Session()
        # Only retry safe GET requests. Never replay account creation or book mutations.
        retry = Retry(total=2, connect=0, backoff_factor=0.5, raise_on_status=False,
                      status_forcelist=[502, 503, 504], allowed_methods={"GET"})
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def request(self, method, path, *, token=None, **kwargs):
        headers = kwargs.pop("headers", {})
        headers = {"Accept": "application/json", **headers}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            return self.session.request(method, f"{BASE_URL}{path}", headers=headers,
                                        timeout=API_TIMEOUT, **kwargs)
        except requests.RequestException as error:
            # Исходная трассировка requests может содержать пароль или токен.
            raise RuntimeError(
                f"HTTP transport error for {method} {path}: {type(error).__name__}"
            ) from None

    def register(self, username, password):
        return self.request("POST", "/Account/v1/User", json={"userName": username, "password": password})

    def token(self, username, password):
        return self.request("POST", "/Account/v1/GenerateToken", json={"userName": username, "password": password})

    def authorize(self, username, password):
        return self.request("POST", "/Account/v1/Authorized", json={"userName": username, "password": password})

    def profile(self, user_id, token):
        return self.request("GET", f"/Account/v1/User/{user_id}", token=token)

    def catalog(self):
        return self.request("GET", "/BookStore/v1/Books")

    def book(self, isbn):
        return self.request("GET", "/BookStore/v1/Book", params={"ISBN": isbn})

    def add(self, user_id, token, isbns):
        return self.request("POST", "/BookStore/v1/Books", token=token,
                            json={"userId": user_id, "collectionOfIsbns": [{"isbn": i} for i in isbns]})

    def delete_one(self, user_id, token, isbn):
        return self.request("DELETE", "/BookStore/v1/Book", token=token,
                            json={"isbn": isbn, "userId": user_id})

    def delete_all(self, user_id, token):
        return self.request("DELETE", "/BookStore/v1/Books", token=token, params={"UserId": user_id})

    def delete_user(self, user_id, token):
        return self.request("DELETE", f"/Account/v1/User/{user_id}", token=token)

    def close(self):
        self.session.close()
