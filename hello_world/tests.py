from django.test import SimpleTestCase


class DashLandingPageTests(SimpleTestCase):
    def test_homepage_promotes_dash_consultant_chat(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dash")
        self.assertContains(response, "Paid consultant chats with M-Pesa built in")
        self.assertContains(response, "payment gateway")
        self.assertContains(response, "Timed consultation rooms")
