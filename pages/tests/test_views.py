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
                self.assertContains(response, "css/app.css")
                self.assertContains(response, "js/api.js")

    def test_landing_lists_exam_placeholders(self):
        response = self.client.get(reverse("pages:home"))
        for name in ("PTE Academic", "PTE Core", "IELTS Academic", "IELTS General"):
            self.assertContains(response, name)
