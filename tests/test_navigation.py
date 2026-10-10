import unittest

from oncemore.navigation import compute


def nav(buttons):
    return compute([(bid, rect, ov) for bid, rect, ov in buttons])


class TestNavigation(unittest.TestCase):
    def test_vertical_list_wraps_and_has_no_sideways_moves(self):
        n = nav([("a", (116, 216, 245, 254), {}),
                 ("b", (115, 276, 266, 314), {}),   # wider, centre slightly right
                 ("c", (115, 336, 337, 374), {})])
        self.assertEqual(n["a"], {"up": "c", "down": "b", "left": "a", "right": "a"})
        self.assertEqual(n["b"]["up"], "a")
        self.assertEqual(n["b"]["down"], "c")
        self.assertEqual(n["c"]["down"], "a")  # wrap to top

    def test_grid_with_bottom_row(self):
        # 3x2 thumbnails + BACK at bottom-left
        g = {}
        for r in range(2):
            for c in range(3):
                g[f"t{r * 3 + c + 1}"] = (50 + c * 216, 80 + r * 170, 240 + c * 216, 236 + r * 170)
        g["back"] = (50, 416, 140, 450)
        n = nav([(k, v, {}) for k, v in g.items()])
        self.assertEqual(n["t1"]["right"], "t2")
        self.assertEqual(n["t2"]["right"], "t3")
        self.assertEqual(n["t3"]["right"], "t1")     # row wrap
        self.assertEqual(n["t1"]["left"], "t3")
        self.assertEqual(n["t1"]["down"], "t4")
        self.assertEqual(n["t2"]["down"], "t5")
        self.assertEqual(n["t4"]["down"], "back")
        self.assertEqual(n["t6"]["down"], "back")    # only thing below
        self.assertEqual(n["back"]["up"], "t4")
        self.assertEqual(n["t1"]["up"], "back")      # column wrap
        self.assertEqual(n["back"]["left"], "back")

    def test_prefers_aligned_over_diagonal(self):
        n = nav([("src", (100, 100, 200, 140), {}),
                 ("below", (100, 300, 200, 340), {}),
                 ("diag", (300, 200, 400, 240), {})])
        self.assertEqual(n["src"]["down"], "below")
        self.assertEqual(n["src"]["right"], "diag")

    def test_override(self):
        n = nav([("a", (0, 0, 10, 10), {"down": "a", "left": "b"}),
                 ("b", (0, 20, 10, 30), {})])
        self.assertEqual(n["a"]["down"], "a")
        self.assertEqual(n["a"]["left"], "b")
        self.assertEqual(n["b"]["up"], "a")

    def test_single_button(self):
        n = nav([("only", (10, 10, 50, 30), {})])
        self.assertEqual(set(n["only"].values()), {"only"})


if __name__ == "__main__":
    unittest.main()
