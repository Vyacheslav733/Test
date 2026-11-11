import json

import allure
import pytest
from requests import Request, Response

from framework.assertions import expect_empty, expect_error, expect_schema
from framework.schemas import BOOK, TOKEN_RESULT

pytestmark = pytest.mark.unit


@pytest.fixture
def make_response():
    def create(payload, status=400):
        response = Response()
        response.status_code = status
        response.request = Request("GET", "https://example.test/check").prepare()
        response._content = json.dumps(payload).encode("utf-8")
        return response
    return create


@pytest.fixture
def book():
    return {
        "isbn": "9781449325862", "title": "Test book", "subTitle": "",
        "author": "Test author", "publish_date": "2020-01-01T00:00:00Z",
        "publisher": "Test publisher", "pages": 1,
        "description": "", "website": "https://example.test/book",
    }


@allure.title("UNIT-01: полная запись книги проходит валидацию")
def test_book_schema_accepts_valid_response(make_response, book):
    with allure.step("Проверить корректную запись книги"):
        assert expect_schema(make_response(book), BOOK) == book


@pytest.mark.parametrize("field", [
    "isbn", "title", "subTitle", "author", "publish_date",
    "publisher", "pages", "description", "website",
])
@allure.title("UNIT-02: отсутствие поля {field} обнаруживается")
def test_book_schema_rejects_missing_field(make_response, book, field):
    del book[field]
    with allure.step("Проверить отказ при отсутствии обязательного поля"):
        with pytest.raises(AssertionError, match="required"):
            expect_schema(make_response(book), BOOK)


@pytest.mark.parametrize(("field", "value", "constraint"), [
    ("publish_date", "yesterday", "format"),
    ("website", "bad URL", "format"),
    ("pages", -1, "minimum"),
    ("pages", "many", "type"),
])
@allure.title("UNIT-03: некорректное значение поля {field} обнаруживается")
def test_book_schema_rejects_invalid_value(make_response, book, field, value, constraint):
    book[field] = value
    with allure.step("Проверить отклонение неправильного формата, типа или диапазона"):
        with pytest.raises(AssertionError, match=constraint):
            expect_schema(make_response(book), BOOK)


@pytest.mark.parametrize("payload", [
    {"token": "test-token", "expires": "2030-01-01T00:00:00Z",
     "status": "Success", "result": "User authorized successfully."},
    {"token": None, "expires": None,
     "status": "Failed", "result": "User authorization failed."},
], ids=["success", "failed"])
@allure.title("UNIT-04: согласованный ответ выдачи токена проходит валидацию")
def test_token_schema_accepts_consistent_response(make_response, payload):
    with allure.step("Проверить согласованность статуса, токена и срока действия"):
        assert expect_schema(make_response(payload), TOKEN_RESULT) == payload


@pytest.mark.parametrize("payload", [
    {"token": None, "expires": "2030-01-01T00:00:00Z", "status": "Success", "result": "OK"},
    {"token": "test-token", "expires": None, "status": "Failed", "result": "Failed"},
    {"token": "test-token", "expires": "yesterday", "status": "Success", "result": "OK"},
], ids=["missing-success-token", "unexpected-failed-token", "invalid-expiration"])
@allure.title("UNIT-05: противоречивый ответ выдачи токена отклоняется")
def test_token_schema_rejects_inconsistent_response(make_response, payload):
    with allure.step("Проверить отклонение противоречивых данных авторизации"):
        with pytest.raises(AssertionError):
            expect_schema(make_response(payload), TOKEN_RESULT)


@allure.title("UNIT-06: ожидаемая причина отказа подтверждается")
def test_expect_error_accepts_matching_reason(make_response):
    payload = {"code": "1205", "message": "Unknown ISBN"}
    with allure.step("Сверить HTTP-статус, код и сообщение"):
        assert expect_error(make_response(payload), 400, code="1205", message_contains="Unknown ISBN") == payload


@pytest.mark.parametrize(("status", "code", "message", "failure"), [
    (401, "1205", "Unknown ISBN", "Expected HTTP"),
    (400, "1200", "Unknown ISBN", "Expected error code"),
    (400, "1205", "Different reason", "Unexpected API error message"),
], ids=["wrong-status", "wrong-code", "wrong-message"])
@allure.title("UNIT-07: другая причина отказа обнаруживается")
def test_expect_error_rejects_mismatch(make_response, status, code, message, failure):
    response = make_response({"code": code, "message": message}, status)
    with allure.step("Убедиться, что несовпадение не принимается за ожидаемый отказ"):
        with pytest.raises(AssertionError, match=failure):
            expect_error(response, 400, code="1205", message_contains="Unknown ISBN")


@pytest.mark.parametrize("omitted", ["code", "message_contains"])
@allure.title("UNIT-08: проверка ошибки требует явно задать {omitted}")
def test_expect_error_requires_reason(make_response, omitted):
    expected = {"code": "1205", "message_contains": "Unknown ISBN"}
    del expected[omitted]
    with allure.step("Проверить обязательность ожидаемых кода и сообщения"):
        with pytest.raises(TypeError, match=omitted):
            expect_error(make_response({"code": "1205", "message": "Unknown ISBN"}), 400, **expected)


@allure.title("UNIT-09: ответ HTTP 204 должен иметь пустое тело")
def test_expect_empty_rejects_body(make_response):
    response = make_response({"unexpected": "body"}, 204)
    with allure.step("Проверить отклонение HTTP 204 с телом"):
        with pytest.raises(AssertionError, match="has a body"):
            expect_empty(response)
    with allure.step("Проверить принятие пустого HTTP 204"):
        response._content = b""
        expect_empty(response)


@allure.title("UNIT-10: HTML вместо JSON обнаруживается")
def test_schema_rejects_non_json(make_response):
    response = make_response(None)
    response._content = b"<html>Error</html>"
    with allure.step("Проверить отклонение ответа другого формата"):
        with pytest.raises(AssertionError, match="not JSON"):
            expect_schema(response, BOOK)


@allure.title("UNIT-11: проверка сообщения допускает регистр, пробелы и пунктуацию")
def test_expect_error_accepts_editorial_changes(make_response):
    payload = {"code": "1205", "message": "  UNKNOWN   ISBN!  "}
    with allure.step("Проверить ключевую фразу при редакционном изменении сообщения"):
        assert expect_error(make_response(payload), 400,
                            code="1205", message_contains="unknown isbn") == payload


@allure.title("UNIT-12: пустая ожидаемая фраза отклоняется")
def test_expect_error_rejects_empty_fragment(make_response):
    with allure.step("Проверить защиту от формальной проверки пустой строки"):
        with pytest.raises(AssertionError, match="must not be empty"):
            expect_error(make_response({"code": "1205", "message": "Unknown ISBN"}),
                         400, code="1205", message_contains="   ")
