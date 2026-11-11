import allure
import pytest
from playwright.sync_api import expect

from framework.config import BASE_URL
from framework.pages.catalog import CatalogPage
from framework.pages.login import LoginPage
from framework.pages.profile import ProfilePage


@pytest.mark.ui
@allure.title("UI-01: вход нового пользователя в профиль")
def test_ui_login(logged_in_page, user):
    with allure.step("Проверить имя пользователя в открытом профиле"):
        expect(logged_in_page.locator("#userName-value")).to_have_text(user.username)


@pytest.mark.ui
@pytest.mark.negative
@allure.title("UI-02: неверный пароль отклоняется")
def test_ui_bad_login(browser_page, user):
    with allure.step("Войти с неверным паролем и проверить сообщение об ошибке"):
        LoginPage(browser_page).open().invalid_login(user.username, "WrongPassword1!")
    with allure.step("Проверить, что профиль пользователя не открыт"):
        expect(browser_page.locator("#userName-value")).to_have_count(0)


@pytest.mark.ui
@allure.title("UI-03: поиск книги, пустая выдача и сброс фильтра")
def test_ui_search(browser_page, catalog):
    page = CatalogPage(browser_page).open()
    first = catalog[0]["title"]
    with allure.step("Найти книгу по полному названию"):
        page.search(first).title_visible(first)
        expect(page.book_links).to_have_text([first])
    with allure.step("Проверить пустую выдачу для несуществующего названия"):
        page.search("not-a-real-book-" + "x" * 16)
        expect(page.book_links).to_have_count(0)
    with allure.step("Очистить поиск и проверить восстановление каталога"):
        page.search("")
        page.title_visible(first)


@pytest.mark.ui
@allure.title("UI-04: список книг совпадает с каталогом API")
def test_catalog_ui_matches_api(browser_page, catalog):
    with allure.step("Открыть магазин и собрать названия со всех страниц"):
        page = CatalogPage(browser_page).open()
        page.title_visible(catalog[0]["title"])
        all_titles = []
        while True:
            all_titles.extend(page.visible_titles())
            next_btn = browser_page.get_by_role("button", name="Next", exact=True)
            if next_btn.count() == 0 or next_btn.is_disabled():
                break
            first = page.book_links.first.inner_text()
            next_btn.click()
            expect(page.book_links.first).not_to_have_text(first)
    with allure.step("Сравнить полный список UI с каталогом API"):
        assert sorted(all_titles) == sorted(book["title"] for book in catalog)


@pytest.mark.ui
@pytest.mark.negative
@allure.title("UI-10: профиль недоступен без авторизации")
def test_profile_without_login(browser_page):
    with allure.step("Открыть профиль в новом контексте без авторизации"):
        profile = ProfilePage(browser_page).open()
    with allure.step("Проверить предложение войти и отсутствие личной коллекции"):
        expect(browser_page.get_by_text(
            "Currently you are not logged into the Book Store application", exact=False
        )).to_be_visible()
        expect(browser_page.get_by_role("link", name="login", exact=True)).to_be_visible()
        expect(browser_page.locator("#userName-value")).to_have_count(0)
        expect(profile.book_links).to_have_count(0)


@pytest.mark.ui
@allure.title("UI-13: сообщение об ошибке входа ожидается дольше пяти секунд")
def test_bad_login_waits_for_delayed_message(browser_page):
    html = """
    <input id="userName">
    <input id="password" type="password">
    <button id="login">Login</button>
    <script>
    document.querySelector("#login").onclick = async () => {
        const response = await fetch("/Account/v1/GenerateToken", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                userName: document.querySelector("#userName").value,
                password: document.querySelector("#password").value
            })
        });
        const payload = await response.json();
        if (payload.status === "Failed") {
            setTimeout(() => {
                const error = document.createElement("p");
                error.id = "name";
                error.textContent = "Invalid username or password!";
                document.body.append(error);
            }, 6500);
        }
    };
    </script>
    """
    with allure.step("Смоделировать отказ авторизации и задержку сообщения на 6,5 секунды"):
        browser_page.route(
            BASE_URL + "/login",
            lambda route: route.fulfill(status=200, content_type="text/html", body=html),
        )
        browser_page.route(
            BASE_URL + "/Account/v1/GenerateToken",
            lambda route: route.fulfill(status=200, json={
                "token": None, "expires": None,
                "status": "Failed", "result": "User authorization failed.",
            }),
        )
    with allure.step("Проверить, что LoginPage дожидается сообщения после ответа API"):
        LoginPage(browser_page).open().invalid_login("test-user", "WrongPassword1!")
