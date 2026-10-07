import csv
import gzip
import os
import sys


def results_present(helper):
    path = getattr(helper, "results_file", None)
    return bool(path) and os.path.exists(path)


def get_events(helper):
    if not results_present(helper):
        return iter(())
    try:
        helper.result_handle = gzip.open(helper.results_file, "rt")
    except FileNotFoundError:
        return iter(())
    except OSError:
        helper.log_error("Error: No search result. Cannot send alert action.")
        sys.exit(2)
    return (
        helper.pre_handle(num, result)
        for num, result in enumerate(csv.DictReader(helper.result_handle))
    )
