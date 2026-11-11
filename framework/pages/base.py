from framework.config import BASE_URL, TIMEOUT_MS

class BasePage:
    def __init__(self, page):
        self.page = page
        self.page.set_default_timeout(TIMEOUT_MS)

    def open(self, route):
        self.page.goto(BASE_URL + route, wait_until="domcontentloaded")
        return self

    def dismiss_overlays(self):
        # Эти элементы относятся к рекламной оболочке DemoQA.
        self.page.locator("#fixedban").evaluate_all("nodes => nodes.forEach(n => n.remove())")
        self.page.locator("footer").evaluate_all("nodes => nodes.forEach(n => n.style.pointerEvents = 'none')")
