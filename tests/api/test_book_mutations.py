import allure
import pytest

from framework.assertions import expect_empty, expect_error, expect_schema, expect_status, wait_books
from framework.schemas import ADDED_BOOKS


@pytest.mark.api
@pytest.mark.parametrize(("count", "case_id"), [(1, "API-05"), (3, "API-06")], ids=["one", "three"])
@allure.title("{case_id}: добавить {count} книг в профиль")
def test_add_books(api, user, catalog, count, case_id):
    books = catalog[:count]
    with allure.step(f"Добавить в коллекцию книг: {count}"):
        response = api.add(user.id, user.token, [book["isbn"] for book in books])
        expect_status(response, 201)
    with allure.step("Проверить структуру ответа и точный набор добавленных ISBN"):
        added = expect_schema(response, ADDED_BOOKS)["books"]
        assert sorted(book["isbn"] for book in added) == sorted(book["isbn"] for book in books)
    with allure.step("Получить профиль и сверить сохранённые книги"):
        stored = wait_books(api, user, [book["isbn"] for book in books])
        assert {book["title"] for book in stored} == {book["title"] for book in books}


@pytest.mark.api
@allure.title("API-07: удалить одну книгу и сохранить остальные")
def test_delete_one(api, user, catalog, seed_books):
    selected = catalog[:3]
    with allure.step("Добавить три книги и проверить исходную коллекцию"):
        seed_books(selected)
    with allure.step("Удалить первую книгу и проверить HTTP 204 без тела"):
        expect_empty(api.delete_one(user.id, user.token, selected[0]["isbn"]))
    with allure.step("Проверить, что остались ровно две другие книги"):
        wait_books(api, user, [book["isbn"] for book in selected[1:]])


@pytest.mark.api
@allure.title("API-08: удалить все книги")
def test_delete_all(api, user, catalog, seed_books):
    selected = catalog[:3]
    with allure.step("Добавить три книги в коллекцию"):
        seed_books(selected)
    with allure.step("Удалить всю коллекцию и проверить HTTP 204 без тела"):
        expect_empty(api.delete_all(user.id, user.token))
    with allure.step("Проверить пустой список книг в профиле"):
        wait_books(api, user, [])


@pytest.mark.api
@pytest.mark.negative
@allure.title("API-09: повторное добавление не дублирует книгу")
def test_duplicate_book(api, user, catalog, seed_books):
    isbn = catalog[0]["isbn"]
    with allure.step("Добавить книгу в коллекцию"):
        seed_books([catalog[0]])
    with allure.step("Повторно добавить тот же ISBN и проверить HTTP 400"):
        expect_error(api.add(user.id, user.token, [isbn]), 400,
                     code="1210", message_contains="already present")
    with allure.step("Проверить, что в коллекции один экземпляр книги"):
        wait_books(api, user, [isbn])


@pytest.mark.api
@pytest.mark.negative
@allure.title("API-16: удаление отсутствующей в коллекции книги сохраняет остальные")
def test_delete_book_not_in_collection(api, user, catalog, seed_books):
    stored, missing = catalog[:2]
    with allure.step("Добавить одну книгу, оставив вторую только в каталоге"):
        seed_books([stored])
    with allure.step("Удалить ISBN второй книги и проверить HTTP 400"):
        expect_error(api.delete_one(user.id, user.token, missing["isbn"]), 400,
                     code="1206", message_contains="not available")
    with allure.step("Проверить, что исходная книга осталась в коллекции"):
        wait_books(api, user, [stored["isbn"]])
