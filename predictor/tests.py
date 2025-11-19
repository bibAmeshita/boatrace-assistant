from __future__ import annotations

import json
from unittest.mock import patch

from django.test import TestCase


class RacePredictionViewTests(TestCase):
    @patch("predictor.views.fetch_race_detail")
    def test_race_prediction_returns_tickets(self, mock_fetch):
        meta = {"date_text": "9月8日", "day_text": "3日目", "type": "一般", "distance": "1800m"}
        base_entry = {
            "lane": 1,
            "avg_st": 0.16,
            "national_win": 6.5,
            "local_win": 6.0,
            "national_2r": 30.0,
            "local_2r": 32.0,
            "motor_2r": 40.0,
            "boat_2r": 41.0,
            "national_3r": 50.0,
            "local_3r": 51.0,
            "motor_3r": 52.0,
            "boat_3r": 53.0,
            "racer_name": "テスト選手",
            "klass": "A1",
        }
        entries = [{**base_entry, "lane": i} for i in range(1, 4)]
        mock_fetch.return_value = meta, entries

        payload = {
            "raceUrl": "https://example.com/race",
            "place": "多摩川",
            "race": "1R",
            "betType": "3連単",
            "method": "通常",
            "points": 3,
        }

        response = self.client.post(
            "/api/race/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("tickets", data)
        self.assertEqual(data["betType"], "3連単")
        self.assertEqual(len(data.get("entries", [])), 3)
        mock_fetch.assert_called_once_with("https://example.com/race")
