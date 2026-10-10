from django.test import SimpleTestCase
from django.urls import reverse


class PublicPagesTests(SimpleTestCase):
    def test_public_pages_render(self):
        for name, template in [
            ("pages:home", "pages/home.html"),
            ("pages:about", "pages/about.html"),
            ("pages:contact", "pages/contact.html"),
        ]:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template)
                self.assertTemplateUsed(response, "base.html")
