from pathlib import Path
import unittest


class HomeNavigationHistoryTests(unittest.TestCase):
    def test_single_page_navigation_is_synced_with_browser_history(self):
        source = (Path(__file__).resolve().parents[1] / "excel_vlookup_api.py").read_text(encoding="utf-8")
        self.assertIn("history.pushState", source)
        self.assertIn("window.addEventListener('popstate'", source)
        self.assertIn("history.back()", source)
        self.assertIn("touchStartX<=24||touchStartX>=window.innerWidth-24", source)

    def test_previous_page_does_not_only_use_an_in_memory_stack(self):
        source = (Path(__file__).resolve().parents[1] / "excel_vlookup_api.py").read_text(encoding="utf-8")
        self.assertIn("function goPreviousPage(){if(pageStack.length>1)history.back()", source)
        self.assertIn("function goNextPage(){history.forward()}", source)


if __name__ == "__main__":
    unittest.main()
