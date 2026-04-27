from __future__ import annotations

import logging

from bmo.logging import setup


def test_setup_sets_root_level():
    setup("WARNING")
    assert logging.getLogger().level == logging.WARNING


def test_setup_idempotent_no_duplicate_handlers():
    setup("INFO")
    n1 = len(logging.getLogger().handlers)
    setup("INFO")
    n2 = len(logging.getLogger().handlers)
    assert n1 == n2
