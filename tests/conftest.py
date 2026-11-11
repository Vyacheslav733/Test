from dataclasses import dataclass, field
from uuid import uuid4
import secrets
import allure
import pytest
from playwright.sync_api import sync_playwright
from framework.api import BookStoreAPI
from framework.assertions import expect_schema, expect_status, wait_books
from framework.config import BASE_URL
from framework.schemas import ADDED_BOOKS, CATALOG, TOKEN_RESULT, USER_CREATED

@dataclass
class User:
    username: str
    password: str = field(repr=False)
    id: str
    token: str = field(repr=False)

@pytest.fixture
def api():
    client = BookStoreAPI()
    try:
        yield client
    finally:
        client.close()

@pytest.fixture
def user(api):
    username = "qa_" + uuid4().hex[:18]
    # DemoQA requires upper/lower/digit/special and min length.
    password = "Qa1!" + secrets.token_urlsafe(15)
    response = api.register(username, password)
    expect_status(response, 201)
    registration = expect_schema(response, USER_CREATED)
    assert registration["username"] == username and not registration["books"]
    user_id = registration["userID"]
    account = User(username, password, user_id, "")
    try:
        with allure.step("Получить токен нового пользователя"):
            token_resp = api.token(username, password)
            expect_status(token_resp, 200)
            token_payload = expect_schema(token_resp, TOKEN_RESULT)
            assert token_payload["token"] and token_payload["status"] == "Success", "Test user token generation failed"
            account.token = token_payload["token"]
        yield account
    finally:
        # Очистка выполняется также при сбое получения токена до запуска теста.
        try:
            response = api.delete_user(account.id, account.token)
            if response.status_code == 401:
                renewed = api.token(account.username, account.password)
                if renewed.status_code == 200:
                    renewed_token = expect_schema(renewed, TOKEN_RESULT)["token"]
                    if renewed_token:
                        response = api.delete_user(account.id, renewed_token)
            if response.status_code != 204:
                allure.attach(f"User cleanup HTTP {response.status_code}",
                              name="cleanup-warning", attachment_type=allure.attachment_type.TEXT)
        except Exception as exc:
            allure.attach(type(exc).__name__, name="cleanup-error", attachment_type=allure.attachment_type.TEXT)

@pytest.fixture
def seed_books(api, user):
    def add(books):
        with allure.step("Подготовить коллекцию для проверяемого действия"):
            isbns = [book["isbn"] for book in books]
            response = api.add(user.id, user.token, isbns)
            expect_status(response, 201)
            added = expect_schema(response, ADDED_BOOKS)["books"]
            assert sorted(book["isbn"] for book in added) == sorted(isbns)
            return wait_books(api, user, isbns)
    return add


@pytest.fixture(scope="session")
def catalog():
    client = BookStoreAPI()
    try:
        result = client.catalog()
    finally:
        client.close()
    expect_status(result, 200)
    books = expect_schema(result, CATALOG)["books"]
    assert len(books) >= 3, "E2E requires at least three catalog books"
    assert len({b["isbn"] for b in books}) == len(books)
    return tuple(books)

@pytest.fixture(scope="session")
def browser(request):
    browser_name = request.config.getoption("--browser-name")
    headless = not request.config.getoption("--headed")
    with sync_playwright() as pw:
        browser_type = getattr(pw, "chromium" if browser_name in ("chrome", "edge") else browser_name)
        options = {"channel": {"chrome": "chrome", "edge": "msedge"}[browser_name]} if browser_name in ("chrome", "edge") else {}
        instance = browser_type.launch(headless=headless, **options)
        try:
            yield instance
        finally:
            instance.close()


@pytest.fixture
def browser_page(browser, request):
    allure.dynamic.parameter("browser", request.config.getoption("--browser-name"))
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="en-US", accept_downloads=False)
    try:
        page = context.new_page()
        yield page
        if any((report := getattr(request.node, f"rep_{phase}", None)) and report.failed
               for phase in ("setup", "call")):
            try:
                allure.attach(page.screenshot(full_page=True, timeout=5000, mask=[page.locator("#password")]),
                              "failure-screenshot", allure.attachment_type.PNG)
                allure.attach(page.url, "failure-url", allure.attachment_type.TEXT)
            except Exception as exc:
                allure.attach(type(exc).__name__, "screenshot-error", allure.attachment_type.TEXT)
    finally:
        context.close()

@pytest.fixture
def logged_in_page(browser_page, user):
    from framework.pages.login import LoginPage
    with allure.step("Войти в профиль временного пользователя"):
        LoginPage(browser_page).open().login(user.username, user.password)
        tokens = [cookie["value"] for cookie in browser_page.context.cookies(BASE_URL)
                  if cookie["name"] == "token" and cookie["value"]]
        assert len(tokens) == 1, "DemoQA did not set a unique session token"
        user.token = tokens[0]
    return browser_page

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)

def pytest_addoption(parser):
    parser.addoption("--browser-name", choices=["chrome", "firefox", "edge", "chromium", "webkit"],
                     default="chrome", help="Браузер для UI-тестов")
    parser.addoption("--headed", action="store_true", help="Show browser window")
