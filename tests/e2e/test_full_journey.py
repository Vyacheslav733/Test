import pytest
import allure
from framework.pages.catalog import CatalogPage
from framework.pages.profile import ProfilePage
from framework.assertions import expect_empty, expect_schema, expect_status, wait_books
from framework.schemas import ADDED_BOOKS, CATALOG


@pytest.mark.api
@pytest.mark.e2e
@allure.title("E2E-03: API — авторизация, каталог, добавление трёх книг, удаление одной")
def test_e2e_api(api, user):
    with allure.step("Проверить авторизацию временного пользователя"):
        response = api.authorize(user.username, user.password)
        expect_status(response, 200)
        assert expect_schema(response, {"type": "boolean"}) is True
    with allure.step("Получить каталог и выбрать три книги"):
        response = api.catalog()
        expect_status(response, 200)
        selected = expect_schema(response, CATALOG)["books"][:3]
        assert len({book["isbn"] for book in selected}) == 3
        isbns = [book["isbn"] for book in selected]
    with allure.step("Добавить три книги в профиль"):
        response = api.add(user.id, user.token, isbns)
        expect_status(response, 201)
        assert sorted(book["isbn"] for book in expect_schema(response, ADDED_BOOKS)["books"]) == sorted(isbns)
        wait_books(api, user, isbns)
    with allure.step("Удалить первую книгу и проверить две оставшиеся"):
        expect_empty(api.delete_one(user.id, user.token, isbns[0]))
        books = wait_books(api, user, isbns[1:])
        assert {book["isbn"]: book["title"] for book in books} == {
            book["isbn"]: book["title"] for book in selected[1:]
        }

@pytest.mark.e2e
@pytest.mark.ui
@allure.title("E2E-01: UI — вход, добавление трёх книг и удаление одной")
def test_e2e_ui_with_api_validation(logged_in_page, api, user, catalog):
    selected = catalog[:3]
    store = CatalogPage(logged_in_page).open()
    with allure.step("Найти и добавить три разные книги через UI"):
        for book in selected:
            store.open_book(book["title"]).add_current_book().go_back_to_store()
    with allure.step("Проверить добавление книг через API профиля"):
        wait_books(api, user, [b["isbn"] for b in selected])
    with allure.step("Удалить первую книгу через UI"):
        profile = ProfilePage(logged_in_page).open()
        profile.assert_books([b["title"] for b in selected])
        profile.delete_one(selected[0]["title"])
    with allure.step("Проверить две оставшиеся книги через UI и API"):
        expected = selected[1:]
        profile.assert_books([b["title"] for b in expected])
        books = wait_books(api, user, [b["isbn"] for b in expected])
        assert {b["title"] for b in books} == {b["title"] for b in expected}

@pytest.mark.e2e
@pytest.mark.ui
@allure.title("E2E-02: API меняет коллекцию, UI показывает результат")
def test_e2e_api_with_ui_validation(logged_in_page, api, user, catalog):
    selected = catalog[:3]
    with allure.step("Добавить три книги через API"):
        expect_status(api.add(user.id, user.token, [b["isbn"] for b in selected]), 201)
        wait_books(api, user, [b["isbn"] for b in selected])
    with allure.step("Проверить коллекцию в браузере"):
        profile = ProfilePage(logged_in_page).open()
        profile.assert_books([b["title"] for b in selected])
    with allure.step("Удалить одну книгу через API"):
        expect_empty(api.delete_one(user.id, user.token, selected[0]["isbn"]))
        wait_books(api, user, [b["isbn"] for b in selected[1:]])
    with allure.step("Повторно открыть профиль и проверить синхронизацию"):
        profile.open().assert_books([b["title"] for b in selected[1:]])
