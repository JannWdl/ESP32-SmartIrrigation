from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")


class UiTests(unittest.TestCase):
    def test_calibration_measurement_uses_confirmed_completed_run(self):
        self.assertIn("calibrationRuns={}", HTML)
        self.assertIn("startCalibrationMeasure", HTML)
        self.assertIn("waitForCalibrationStop", HTML)
        self.assertIn("confirmed.completed", HTML)
        self.assertIn("confirmed.seconds", HTML)
        self.assertNotRegex(
            HTML,
            re.compile(r"flow_ml_s\s*=\s*Number\(ml\.value\)\s*/\s*Number\(sec\.value\)"),
        )

    def test_hidden_sections_are_css_hidden(self):
        self.assertIn("section[hidden]{display:none}", HTML)


if __name__ == "__main__":
    unittest.main()
