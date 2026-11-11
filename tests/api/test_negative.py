import json

import allure
import pytest

from framework.assertions import expect_error, expect_schema, expect_status, wait_books
from framework.schemas import ERROR, TOKEN_RESULT


@pytest.mark.api
@pytest.mark.negative
@allure.title("API-10: неверный пароль не даёт авторизоваться")
def test_wrong_password(api, user):
    with allure.step("Отправить неверный пароль существующего пользователя"):
        result = api.authorize(user.username, "DefinitelyWrong1!")
    with allure.step("Проверить HTTP 404 и JSON с сообщением об ошибке"):
        expect_error(result, 404, code="1207", message_contains="not found")


@pytest.mark.api
@pytest.mark.negative
@allure.title("API-11: неверный пароль не выдаёт токен")
def test_wrong_password_token(api, user):
    with allure.step("Запросить токен с неверным паролем"):
        result = api.token(user.username, "DefinitelyWrong1!")
        expect_status(result, 200)
    with allure.step("Проверить структуру ответа и отсутствие успешного токена"):
        payload = expect_schema(result, TOKEN_RESULT)
        assert payload["status"] == "Failed"
        assert payload["token"] is None and payload["expires"] is None
        assert payload["result"] == "User authorization failed."


@pytest.mark.api
@pytest.mark.negative
@pytest.mark.parametrize("operation", ["add", "delete_one", "delete_all", "profile"])
@allure.title("API-12: операция {operation} недоступна без токена")
def test_missing_authorization(api, user, catalog, operation, seed_books):
    isbn = catalog[0]["isbn"]
    with allure.step("Подготовить исходную коллекцию для проверяемой операции"):
        if operation in {"delete_one", "delete_all"}:
            seed_books([catalog[0]])
    with allure.step(f"Выполнить операцию {operation} без заголовка Authorization"):
        if operation == "add":
            result = api.add(user.id, "", [isbn])
        elif operation == "delete_one":
            result = api.delete_one(user.id, "", isbn)
        elif operation == "delete_all":
            result = api.delete_all(user.id, "")
        else:
            result = api.profile(user.id, "")
    with allure.step("Проверить отказ в доступе и сохранение исходной коллекции"):
        expect_error(result, 401, code="1200", message_contains="not authorized")
        wait_books(api, user, [isbn] if operation in {"delete_one", "delete_all"} else [])


@pytest.mark.api
@pytest.mark.negative
@allure.title("API-13: нельзя добавить неизвестный ISBN")
def test_invalid_isbn(api, user):
    with allure.step("Добавить ISBN, которого нет в каталоге"):
        result = api.add(user.id, user.token, ["0000000000000"])
    with allure.step("Проверить HTTP 400 и пустую коллекцию"):
        expect_error(result, 400, code="1205", message_contains="not available")
        wait_books(api, user, [])


@pytest.mark.api
@pytest.mark.negative
@allure.title("API-14: некорректная структура запроса отклоняется")
def test_invalid_payload(api, user):
    with allure.step("Проверить авторизацию и пустой профиль перед ошибочным запросом"):
        authorized = api.authorize(user.username, user.password)
        expect_status(authorized, 200)
        assert expect_schema(authorized, {"type": "boolean"}) is True
        wait_books(api, user, [])
    with allure.step("Передать строку вместо массива ISBN"):
        result = api.request("POST", "/BookStore/v1/Books", token=user.token,
                             json={"userId": user.id, "collectionOfIsbns": "invalid"})
    with allure.step("Проверить отказ в обработке и сохранение пустой коллекции"):
        details = {
            "method": result.request.method,
            "path": "/BookStore/v1/Books",
            "status": result.status_code,
            "content_type": result.headers.get("Content-Type", ""),
            "known_server_error": "collectionOfIsbns.map is not a function" in result.text,
        }
        allure.attach(json.dumps(details, ensure_ascii=False, indent=2),
                      "API-14: статус и формат ответа", allure.attachment_type.JSON)
        if result.status_code == 500 and details["known_server_error"]:
            wait_books(api, user, [])
            pytest.xfail("DEMOQA-01: сервис возвращает HTTP 500 вместо ошибки валидации 4xx")
        assert result.status_code in (400, 422), f"Expected validation error, got HTTP {result.status_code}"
        expect_schema(result, ERROR)
        wait_books(api, user, [])
