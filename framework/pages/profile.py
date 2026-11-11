from playwright.sync_api import expect
from framework.pages.base import BasePage

class ProfilePage(BasePage):
    def open(self):
        return super().open("/profile")

    def assert_books(self, titles):
        for title in titles:
            expect(self.page.get_by_role("link", name=title, exact=True)).to_be_visible()
        # Auto-retry while the browser finishes rendering the updated profile.
        expect(self.book_links).to_have_count(len(titles))
        actual = self.books()
        assert sorted(actual) == sorted(titles), f"Profile books: {actual}"

    @property
    def book_links(self):
        return self.page.locator("table tbody a[href^='/books?search='], .rt-tbody a[href^='/profile?book=']")

    @property
    def confirmation_dialog(self):
        return self.page.locator(".modal-content")

    def books(self):
        return self.book_links.all_text_contents()

    def delete_one(self, title, *, confirm=True):
        row = self.page.locator("table tbody tr, .rt-tr-group").filter(
            has=self.page.get_by_role("link", name=title, exact=True)
        )
        expect(row).to_be_visible()
        self.dismiss_overlays()
        row.locator("[id^='delete-record-']").click()
        modal = self.confirmation_dialog
        expect(modal).to_be_visible()
        if confirm:
            def accept_dialog(dialog):
                dialog.accept()
            self.page.on("dialog", accept_dialog)
            try:
                modal.get_by_role("button", name="OK", exact=True).click()
                expect(self.page.get_by_role("link", name=title, exact=True)).to_have_count(0)
            finally:
                self.page.remove_listener("dialog", accept_dialog)
        else:
            modal.get_by_role("button", name="Cancel", exact=True).click()
            expect(modal).to_be_hidden()
            expect(self.page.get_by_role("link", name=title, exact=True)).to_be_visible()

    def delete_all(self, *, confirm=True):
        self.dismiss_overlays()
        self.page.get_by_role("button", name="Delete All Books", exact=True).click()
        modal = self.confirmation_dialog
        expect(modal).to_be_visible()
        if not confirm:
            modal.get_by_role("button", name="Cancel", exact=True).click()
            expect(modal).to_be_hidden()
            return
        with self.page.expect_response(
            lambda response: response.request.method == "DELETE"
            and response.url.split("?")[0].endswith("/BookStore/v1/Books")
        ) as deletion:
            modal.get_by_role("button", name="OK", exact=True).click()
        assert deletion.value.status == 204, f"Delete All Books status: {deletion.value.status}"
