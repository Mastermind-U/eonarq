import os
import sys

import pytest


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if not report.failed or os.getenv("GITHUB_ACTIONS") != "true":
        return
    message = report.longreprtext[-12000:]
    message = (
        message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    )
    path, line, _ = report.location
    sys.stdout.write(
        f"::error file={path},line={(line or 0) + 1},"
        f"title=Browser test failure::{message}\n",
    )
