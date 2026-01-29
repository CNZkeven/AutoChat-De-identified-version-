import unittest
from datetime import datetime

from backend.app.services import graduation_requirements as gr


class TestProgramVersionSelection(unittest.TestCase):
    def test_extract_year(self):
        self.assertEqual(gr._extract_version_year("2021版"), 2021)
        self.assertEqual(gr._extract_version_year("培养方案2020"), 2020)
        self.assertIsNone(gr._extract_version_year("无年份"))
        self.assertIsNone(gr._extract_version_year(None))

    def test_select_version_by_grade(self):
        versions = [
            {"program_version_id": 1, "version_name": "2018版", "updated_at": datetime(2020, 1, 1)},
            {"program_version_id": 2, "version_name": "2020版", "updated_at": datetime(2021, 1, 1)},
            {"program_version_id": 3, "version_name": "2022版", "updated_at": datetime(2022, 1, 1)},
            {"program_version_id": 4, "version_name": "2023版", "updated_at": datetime(2023, 1, 1)},
        ]
        picked = gr._select_program_version(versions, 2022)
        self.assertEqual(picked["program_version_id"], 3)

    def test_select_version_fallback_latest(self):
        versions = [
            {"program_version_id": 1, "version_name": "2020版", "updated_at": datetime(2020, 1, 1)},
            {"program_version_id": 2, "version_name": "2021版", "updated_at": datetime(2021, 6, 1)},
        ]
        picked = gr._select_program_version(versions, 2019)
        self.assertEqual(picked["program_version_id"], 2)

    def test_select_version_uses_updated_at_when_no_year(self):
        versions = [
            {"program_version_id": 1, "version_name": "旧版", "updated_at": datetime(2020, 1, 1)},
            {"program_version_id": 2, "version_name": "新版", "updated_at": datetime(2022, 1, 1)},
        ]
        picked = gr._select_program_version(versions, 2021)
        self.assertEqual(picked["program_version_id"], 2)

    def test_select_version_ties_use_updated_at(self):
        versions = [
            {"program_version_id": 1, "version_name": "2021版", "updated_at": datetime(2021, 1, 1)},
            {"program_version_id": 2, "version_name": "2021版", "updated_at": datetime(2021, 6, 1)},
        ]
        picked = gr._select_program_version(versions, 2021)
        self.assertEqual(picked["program_version_id"], 2)


if __name__ == "__main__":
    unittest.main()
