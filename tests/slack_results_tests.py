import csv
import gzip
import io
import os
import shutil
import tempfile
import unittest

import slack_results

READ_ERROR = "Error: No search result. Cannot send alert action."


class FakeHelper(object):
    def __init__(self, results_file):
        self.results_file = results_file
        self.result_handle = None
        self.errors = []

    def log_error(self, msg):
        self.errors.append(msg)

    def pre_handle(self, num, result):
        result.setdefault("rid", str(num))
        return result


def write_gzipped_csv(path, rows, fieldnames):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    with gzip.open(path, "wt") as handle:
        handle.write(buffer.getvalue())


class ResultsTestCase(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.directory, True)

    def path(self, name):
        return os.path.join(self.directory, name)


class ResultsPresentTests(ResultsTestCase):
    def test_absent_path_is_not_present(self):
        helper = FakeHelper(self.path("missing.csv.gz"))
        self.assertFalse(slack_results.results_present(helper))

    def test_none_path_is_not_present(self):
        self.assertFalse(slack_results.results_present(FakeHelper(None)))

    def test_empty_path_is_not_present(self):
        self.assertFalse(slack_results.results_present(FakeHelper("")))

    def test_missing_attribute_is_not_present(self):
        class Bare(object):
            pass

        self.assertFalse(slack_results.results_present(Bare()))

    def test_real_file_is_present(self):
        path = self.path("results.csv.gz")
        write_gzipped_csv(path, [{"_raw": "a"}], ["_raw"])
        self.assertTrue(slack_results.results_present(FakeHelper(path)))


class GetEventsAbsenceTests(ResultsTestCase):
    def test_absent_file_yields_no_events(self):
        helper = FakeHelper(self.path("missing.csv.gz"))
        self.assertEqual(list(slack_results.get_events(helper)), [])

    def test_absent_file_does_not_exit(self):
        helper = FakeHelper(self.path("missing.csv.gz"))
        slack_results.get_events(helper)
        self.assertEqual(helper.errors, [])

    def test_none_results_file_yields_no_events(self):
        helper = FakeHelper(None)
        self.assertEqual(list(slack_results.get_events(helper)), [])

    def test_none_results_file_does_not_exit(self):
        helper = FakeHelper(None)
        slack_results.get_events(helper)
        self.assertEqual(helper.errors, [])


class GetEventsRowTests(ResultsTestCase):
    def rows(self):
        path = self.path("results.csv.gz")
        write_gzipped_csv(
            path,
            [{"_raw": "first"}, {"_raw": "second"}],
            ["_raw"],
        )
        self.helper = FakeHelper(path)
        return list(slack_results.get_events(self.helper))

    def test_one_dict_per_row(self):
        rows = self.rows()
        self.assertEqual(len(rows), 2)
        self.assertEqual([row["_raw"] for row in rows], ["first", "second"])

    def test_every_row_carries_a_rid(self):
        for row in self.rows():
            self.assertTrue(row["rid"])

    def test_rows_come_back_through_pre_handle(self):
        rows = self.rows()
        self.assertEqual([row["rid"] for row in rows], ["0", "1"])

    def test_handle_is_published_on_the_helper(self):
        self.rows()
        self.assertIsNotNone(self.helper.result_handle)


class GetEventsFailureTests(ResultsTestCase):
    def test_unreadable_path_exits_two(self):
        path = self.path("results_directory")
        os.makedirs(path)
        helper = FakeHelper(path)
        with self.assertRaises(SystemExit) as caught:
            slack_results.get_events(helper)
        self.assertEqual(caught.exception.code, 2)

    def test_unreadable_path_logs_the_base_class_error_string(self):
        path = self.path("results_directory")
        os.makedirs(path)
        helper = FakeHelper(path)
        try:
            slack_results.get_events(helper)
        except SystemExit:
            pass
        self.assertEqual(helper.errors, [READ_ERROR])

    def test_corrupt_gzip_is_not_silenced(self):
        path = self.path("results.csv.gz")
        with open(path, "wb") as handle:
            handle.write(b"this is not a gzip stream")
        helper = FakeHelper(path)
        with self.assertRaises(OSError):
            list(slack_results.get_events(helper))

    def test_corrupt_gzip_is_present_so_absence_never_swallows_it(self):
        path = self.path("results.csv.gz")
        with open(path, "wb") as handle:
            handle.write(b"this is not a gzip stream")
        self.assertTrue(slack_results.results_present(FakeHelper(path)))


if __name__ == "__main__":
    unittest.main()
