import pytest
import allure
from playwright.sync_api import expect
from framework.pages.catalog import CatalogPage
from framework.pages.profile import ProfilePage
from framework.assertions import wait_books

@pytest.mark.ui
@allure.title("UI-05: добавить одну книгу через магазин")
def test_ui_add_one(logged_in_page, api, user, catalog):
    selected = catalog[0]
    with allure.step("Добавить книгу из карточки магазина"):
        store = CatalogPage(logged_in_page).open()
        store.open_book(selected["title"]).add_current_book()
    with allure.step("Проверить добавленную книгу через API и в профиле"):
        wait_books(api, user, [selected["isbn"]])
        ProfilePage(logged_in_page).open().assert_books([selected["title"]])

@pytest.mark.ui
@allure.title("UI-06: добавить три книги, удалить одну и очистить коллекцию")
def test_ui_add_and_delete_multiple(logged_in_page, api, user, catalog):
    selected = catalog[:3]
    remaining = selected[1:]
    with allure.step("Добавить три книги и проверить коллекцию в профиле"):
        store = CatalogPage(logged_in_page).open()
        for book in selected:
            store.open_book(book["title"]).add_current_book().go_back_to_store()
        wait_books(api, user, [book["isbn"] for book in selected])
        profile = ProfilePage(logged_in_page).open()
        profile.assert_books([book["title"] for book in selected])
    with allure.step("Удалить одну книгу и проверить две оставшиеся"):
        profile.delete_one(selected[0]["title"])
        wait_books(api, user, [book["isbn"] for book in remaining])
        profile.assert_books([book["title"] for book in remaining])
    with allure.step("Очистить коллекцию через UI и проверить, что API возвращает пустой список"):
        profile.delete_all()
        wait_books(api, user, [])
    with allure.step("Повторно открыть профиль и проверить пустой список"):
        profile.open().assert_books([])

@pytest.mark.ui
@allure.title("UI-07: показать книги, добавленные через API")
def test_ui_profile_from_api(logged_in_page, api, user, catalog, seed_books):
    selected = catalog[:2]
    with allure.step("Добавить две книги через API и проверить сохранение"):
        seed_books(selected)
    with allure.step("Открыть профиль и проверить обе книги в интерфейсе"):
        ProfilePage(logged_in_page).open().assert_books([b["title"] for b in selected])


@pytest.mark.ui
@pytest.mark.negative
@allure.title("UI-08: повторное добавление не дублирует книгу")
def test_ui_duplicate_book(logged_in_page, api, user, catalog):
    selected = catalog[0]
    store = CatalogPage(logged_in_page).open().open_book(selected["title"])
    with allure.step("Добавить книгу и получить предупреждение при повторе"):
        store.add_current_book().add_current_book("already")
    with allure.step("Убедиться, что в профиле только один экземпляр книги"):
        wait_books(api, user, [selected["isbn"]])
        ProfilePage(logged_in_page).open().assert_books([selected["title"]])


@pytest.mark.ui
@pytest.mark.negative
@allure.title("UI-09: отмена удаления сохраняет книгу")
def test_ui_cancel_deletion(logged_in_page, api, user, catalog, seed_books):
    selected = catalog[0]
    seed_books([selected])
    profile = ProfilePage(logged_in_page).open()
    with allure.step("Открыть подтверждение удаления и нажать Cancel"):
        profile.assert_books([selected["title"]])
        profile.delete_one(selected["title"], confirm=False)
    with allure.step("Проверить сохранение книги в UI и API"):
        profile.assert_books([selected["title"]])
        wait_books(api, user, [selected["isbn"]])


@pytest.mark.ui
@pytest.mark.negative
@allure.title("UI-11: отмена очистки коллекции сохраняет все книги")
def test_ui_cancel_delete_all(logged_in_page, api, user, catalog, seed_books):
    selected = catalog[:2]
    isbns = [book["isbn"] for book in selected]
    titles = [book["title"] for book in selected]
    with allure.step("Добавить две книги и открыть профиль"):
        seed_books(selected)
        profile = ProfilePage(logged_in_page).open()
        profile.assert_books(titles)
    with allure.step("Нажать Delete All Books и отменить действие кнопкой Cancel"):
        profile.delete_all(confirm=False)
    with allure.step("Проверить обе книги через API и после повторного открытия профиля"):
        wait_books(api, user, isbns)
        profile.assert_books(titles)
        profile.open().assert_books(titles)


@pytest.mark.ui
@allure.title("UI-12: после очистки профиль обновляется без перезагрузки")
def test_ui_delete_all_updates_profile(logged_in_page, api, user, catalog, seed_books):
    selected = catalog[:2]
    titles = [book["title"] for book in selected]
    with allure.step("Добавить две книги и проверить исходный список"):
        seed_books(selected)
        profile = ProfilePage(logged_in_page).open()
        profile.assert_books(titles)
    with allure.step("Подтвердить очистку и проверить удаление книг на сервере"):
        profile.delete_all()
        wait_books(api, user, [])
    with allure.step("Проверить обновление списка и закрытие окна без перезагрузки"):
        modal = profile.confirmation_dialog
        try:
            expect(profile.book_links).to_have_count(0)
        except AssertionError:
            if sorted(profile.books()) == sorted(titles) and modal.is_visible():
                allure.attach(logged_in_page.screenshot(full_page=True),
                              "DEMOQA-02: устаревший список после HTTP 204",
                              allure.attachment_type.PNG)
                allure.attach("Серверная коллекция пуста. В профиле видны обе прежние книги, окно подтверждения открыто.",
                              "DEMOQA-02: наблюдаемое состояние", allure.attachment_type.TEXT)
                pytest.xfail("DEMOQA-02: коллекция удалена, но список и окно подтверждения не обновились")
            raise
        expect(modal).to_be_hidden()
