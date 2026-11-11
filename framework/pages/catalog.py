from playwright.sync_api import expect
from framework.pages.base import BasePage
from framework.config import BASE_URL

class CatalogPage(BasePage):
    def open(self):
        return super().open("/books")

    @property
    def search_box(self):
        return self.page.locator("#searchBox")

    @property
    def book_links(self):
        return self.page.locator("table tbody a[href^='/books?search='], .rt-tbody a[href^='/books?book=']")

    def search(self, term):
        self.search_box.fill(term)
        return self

    def title_visible(self, title):
        expect(self.page.get_by_role("link", name=title, exact=True)).to_be_visible()

    def open_book(self, title):
        self.page.get_by_role("link", name=title, exact=True).click()
        expect(self.page.locator("#ISBN-wrapper")).to_be_visible()
        return self

    def add_current_book(self, message_contains="added"):
        self.dismiss_overlays()
        button = self.page.get_by_role("button", name="Add To Your Collection", exact=True)
        def accept_dialog(dialog):
            dialog.accept()
        self.page.on("dialog", accept_dialog)
        try:
            with self.page.expect_event("dialog") as alert:
                button.click()
            message = alert.value.message
        finally:
            self.page.remove_listener("dialog", accept_dialog)
        assert message_contains in message.lower(), f"Unexpected add-book dialog: {message!r}"
        return self

    def go_back_to_store(self):
        self.dismiss_overlays()
        self.page.get_by_role("button", name="Back To Book Store").click()
        expect(self.page).to_have_url(BASE_URL + "/books")
        return self

    def visible_titles(self):
        return self.book_links.all_text_contents()
