import math
import importlib.util
import unittest

from collective_lab.precision_v16 import CELLS, planning_scenario, stratified_interval


class PrecisionV16Tests(unittest.TestCase):
    def test_planning_table_and_power_decline_with_dispersion(self):
        rows = [planning_scenario(sd) for sd in (.1, .2, .3, .5)]
        self.assertEqual([r["balanced_n_to_review"] for r in rows], [36, 126, 288, 792])
        self.assertTrue(all(a["approximate_power"] > b["approximate_power"] for a, b in zip(rows, rows[1:])))
        self.assertTrue(all(not r["automatic_sample_size_approval"] for r in rows))

    @unittest.skipUnless(importlib.util.find_spec("scipy"), "Requires requirements-evaluation-v16.txt")
    def test_unequal_cell_sizes_do_not_change_equal_cell_estimand(self):
        cells = {cell: [-.1, 0, .1] for cell in CELLS}
        cells[CELLS[0]] = [.1, .2, .3, .2]
        result = stratified_interval(cells)
        self.assertAlmostEqual(result["estimate"], .2/9)
        self.assertEqual(result["n"], 28)
        self.assertLess(result["approximate_interval"][0], result["estimate"])
        self.assertGreater(result["approximate_interval"][1], result["estimate"])

    @unittest.skipUnless(importlib.util.find_spec("scipy"), "Requires requirements-evaluation-v16.txt")
    def test_balanced_equal_variances_reduce_to_standard_paired_interval(self):
        from scipy.stats import t
        result = stratified_interval({cell: [0, .1, .2] for cell in CELLS})
        self.assertAlmostEqual(result["estimate"], .1)
        self.assertAlmostEqual(result["standard_error"], math.sqrt(.01/27))
        self.assertAlmostEqual(result["degrees_of_freedom"], 18)
        self.assertAlmostEqual(result["approximate_interval"][1], .1+t.ppf(.975, 18)*math.sqrt(.01/27))

    def test_no_significance_claim_from_zero_observed_variance(self):
        result = stratified_interval({cell: [.1, .1, .1] for cell in CELLS})
        self.assertIsNone(result["approximate_interval"])
        self.assertFalse(result["automatic_promotion"])
        self.assertLess(result["bounded_independent_task_interval"][0], 0)

    def test_missing_cells_and_nonfinite_values_rejected(self):
        with self.assertRaises(ValueError):
            stratified_interval({CELLS[0]: [0, 1]})
        for invalid in (float('nan'), float('inf'), 3, True):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                stratified_interval({cell: [0, invalid] for cell in CELLS})

    def test_invalid_planning_inputs_rejected(self):
        for sd in (0, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                planning_scenario(sd)
