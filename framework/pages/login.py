from playwright.sync_api import expect
from framework.pages.base import BasePage
from framework.config import BASE_URL

class LoginPage(BasePage):
    def open(self):
        return super().open("/login")

    def login(self, username, password):
        self.page.locator("#userName").fill(username)
        self.page.locator("#password").fill(password)
        self.page.locator("#login").click()
        expect(self.page).to_have_url(BASE_URL + "/profile", timeout=25000)
        return self

    def invalid_login(self, username, password):
        self.page.locator("#userName").fill(username)
        self.page.locator("#password").fill(password)
        self.page.locator("#login").click()
        expect(self.page.locator("#name")).to_contain_text("Invalid username or password!")
