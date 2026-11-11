import time
import allure
from jsonschema import Draft202012Validator, FormatChecker
from framework.schemas import ERROR, PROFILE


def expect_status(response, status):
    with allure.step(f"HTTP {response.request.method} {response.request.path_url}: expected {status}"):
        assert response.status_code == status, f"Expected HTTP {status}, got {response.status_code}"


def expect_schema(response, schema):
    try:
        payload = response.json()
    except ValueError:
        raise AssertionError("The API response is not JSON") from None
    error = next(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(payload), None)
    if error is not None:
        field = ".".join(map(str, error.absolute_path)) or "<root>"
        raise AssertionError(f"Invalid JSON at {field}: {error.validator} constraint")
    return payload


def expect_empty(response):
    expect_status(response, 204)
    assert response.content == b"", "HTTP 204 response has a body"


def expect_error(response, status, *, code, message_contains):
    expect_status(response, status)
    payload = expect_schema(response, ERROR)
    assert payload["code"] == code, f"Expected error code {code}, got {payload['code']}"
    expected = " ".join(message_contains.casefold().split())
    assert expected, "Expected error message fragment must not be empty"
    actual = " ".join(payload["message"].casefold().split())
    assert expected in actual, "Unexpected API error message"
    return payload


def wait_books(api, user, expected_isbns, timeout=12):
    """Read-after-write sync for eventually consistent API, no blind fixed sleep."""
    deadline = time.monotonic() + timeout
    expected = sorted(expected_isbns)
    while True:
        response = api.profile(user.id, user.token)
        expect_status(response, 200)
        payload = expect_schema(response, PROFILE)
        assert payload["userId"] == user.id, "Profile belongs to a different user"
        books = payload["books"]
        last = sorted(book["isbn"] for book in books)
        if last == expected:
            return books
        if time.monotonic() >= deadline:
            raise AssertionError(f"Expected profile ISBNs {expected}, got {last}")
        time.sleep(0.35)
