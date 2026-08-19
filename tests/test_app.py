import os
import tempfile
import unittest

from app import create_app


class PurchaseTrackerTestCase(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": self.db_path,
                "SECRET_KEY": "test",
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_add_edit_delete_purchase(self):
        response = self.client.post(
            "/add",
            data={
                "store": "Target",
                "item": "Baseball cards",
                "order_number": "T123",
                "carrier": "UPS",
                "tracking_number": "1Z999AA10123456784",
                "order_date": "2026-08-18",
                "arrival_date": "2026-08-20",
                "status": "Shipped",
                "notes": "Hobby order",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Baseball cards", response.data)
        self.assertIn(b"1Z999AA10123456784", response.data)
        self.assertIn(b"ups.com/track", response.data)

        response = self.client.post(
            "/edit/1",
            data={
                "store": "Walmart",
                "item": "Baseball card sleeves",
                "order_number": "W123",
                "carrier": "FedEx",
                "tracking_number": "123456789012",
                "order_date": "2026-08-18",
                "arrival_date": "2026-08-21",
                "status": "In Transit",
                "notes": "",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Baseball card sleeves", response.data)
        self.assertIn(b"fedex.com/fedextrack", response.data)

        response = self.client.post("/delete/1", follow_redirects=True)
        self.assertIn(b"No purchases yet", response.data)

    def test_item_is_required(self):
        response = self.client.post(
            "/add",
            data={
                "store": "Target",
                "item": "",
                "carrier": "UPS",
                "status": "Ordered",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Item is required.", response.data)


if __name__ == "__main__":
    unittest.main()
