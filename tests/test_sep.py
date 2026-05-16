import unittest

from sep_to_ebook.sep import extract_entry, prepare_formula


class SepExtractionTests(unittest.TestCase):
    def test_extract_entry_splits_body_and_bibliography(self) -> None:
        html = """
        <html>
          <body>
            <h1>Example Entry</h1>
            <p>First published Wed Jan 1, 2020</p>
            <p>Intro paragraph.</p>
            <ul>
              <li><a href="#s1">1. Section</a></li>
              <li><a href="#bibliography">Bibliography</a></li>
            </ul>
            <p>* * *</p>
            <h2 id="s1">1. Section</h2>
            <p>Main body text.</p>
            <h2 id="bibliography">Bibliography</h2>
            <h3>Works Cited</h3>
            <p>Book A.</p>
            <h2>Academic Tools</h2>
            <p>Ignore me.</p>
          </body>
        </html>
        """

        entry = extract_entry(html, "https://plato.stanford.edu/entries/example/")

        self.assertEqual(entry.title, "Example Entry")
        self.assertIn("Intro paragraph.", entry.summary_html)
        self.assertIn("Main body text.", entry.body_html)
        self.assertIn("Book A.", entry.bibliography_html)
        self.assertNotIn("Ignore me.", entry.bibliography_html)

    def test_math_is_converted_to_mathml_friendly_input(self) -> None:
        html = r"""
        <html>
          <body>
            <h1>Math Entry</h1>
            <p>First published Wed Jan 1, 2020</p>
            <h2>1. Section</h2>
            <p>State is \( \psi \).</p>
            \[\tag{2}\label{ex2} q(j) = \sum_{i=1}^{d^2} [(d+1) p(i) -1/d].r(j\mathbin{|}i) \]
            <p>See Equation \((\ref{ex2})\).</p>
          </body>
        </html>
        """

        entry = extract_entry(html, "https://plato.stanford.edu/entries/math-entry/")

        self.assertIn("<math ", entry.body_html)
        self.assertIn("math-display", entry.body_html)
        self.assertIn("(2)", entry.body_html)
        self.assertNotIn(r"\[", entry.body_html)
        self.assertNotIn(r"\(", entry.body_html)

    def test_prepare_formula_resolves_sep_specific_commands(self) -> None:
        prepared, eq_number = prepare_formula(
            r"\tag{2}\label{ex2} q(j) = \sum_{i=1}^{d^2} [(d+1) p(i) -1/d].r(j\mathbin{|}i)",
            {"ex2": "2"},
        )

        self.assertEqual(eq_number, "2")
        self.assertNotIn(r"\tag", prepared)
        self.assertNotIn(r"\label", prepared)
        self.assertIn(r" \mid ", prepared)


if __name__ == "__main__":
    unittest.main()
