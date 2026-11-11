import allure
import pytest

from framework.assertions import expect_error, expect_schema, expect_status
from framework.schemas import BOOK, PROFILE


@pytest.mark.api
@allure.title("API-01: получить каталог с уникальными ISBN")
def test_catalog_success(catalog):
    with allure.step("Проверить названия и уникальность ISBN каталога"):
        assert all(book["title"] for book in catalog)
        assert len({book["isbn"] for book in catalog}) == len(catalog)


@pytest.mark.api
@allure.title("API-02: карточка книги совпадает с каталогом")
def test_get_book(api, catalog):
    book = catalog[0]
    with allure.step("Запросить карточку книги по ISBN и проверить HTTP 200"):
        response = api.book(book["isbn"])
        expect_status(response, 200)
    with allure.step("Проверить JSON Schema и совпадение ISBN и названия"):
        payload = expect_schema(response, BOOK)
        assert payload["isbn"] == book["isbn"]
        assert payload == book


@pytest.mark.api
@allure.title("API-03: коллекция нового пользователя пуста")
def test_new_profile(api, user):
    with allure.step("Получить профиль нового пользователя"):
        response = api.profile(user.id, user.token)
        expect_status(response, 200)
    with allure.step("Проверить структуру профиля, идентификатор и пустую коллекцию"):
        payload = expect_schema(response, PROFILE)
        assert payload["userId"] == user.id
        assert payload["books"] == []


@pytest.mark.api
@allure.title("API-04: новый пользователь успешно авторизуется")
def test_authorized(api, user):
    with allure.step("Проверить авторизацию с верными реквизитами"):
        response = api.authorize(user.username, user.password)
        expect_status(response, 200)
    with allure.step("Проверить, что JSON-ответ равен true"):
        assert expect_schema(response, {"type": "boolean"}) is True


@pytest.mark.api
@pytest.mark.negative
@allure.title("API-15: запрос отсутствующей в каталоге книги")
def test_unknown_book(api):
    with allure.step("Запросить неизвестный ISBN"):
        response = api.book("0000000000000")
    with allure.step("Проверить HTTP 400 и структуру сообщения об ошибке"):
        expect_error(response, 400, code="1205", message_contains="not available")
