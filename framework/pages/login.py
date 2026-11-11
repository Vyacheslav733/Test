from playwright.sync_api import expect
from framework.pages.base import BasePage
from framework.config import BASE_URL, TIMEOUT_MS

class LoginPage(BasePage):
    def open(self):
        return super().open("/login")

    def login(self, username, password):
        self.page.locator("#userName").fill(username)
        self.page.locator("#password").fill(password)
        self.page.locator("#login").click()
        expect(self.page).to_have_url(BASE_URL + "/profile", timeout=TIMEOUT_MS)
        return self

    def invalid_login(self, username, password):
        self.page.locator("#userName").fill(username)
        self.page.locator("#password").fill(password)
        with self.page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url == BASE_URL + "/Account/v1/GenerateToken",
            timeout=TIMEOUT_MS,
        ) as authentication:
            self.page.locator("#login").click()
        response = authentication.value
        assert response.status == 200, f"GenerateToken HTTP {response.status}"
        payload = response.json()
        assert payload["status"] == "Failed" and payload["token"] is None, "Unexpected login result"
        expect(self.page.locator("#name")).to_contain_text(
            "Invalid username or password!", timeout=TIMEOUT_MS
        )
