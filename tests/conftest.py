from __future__ import annotations

import pytest

from idea_collector.db import IdeaStore
from tests.helpers import sample_config


@pytest.fixture
def config():
    return sample_config()


@pytest.fixture
def store():
    idea_store = IdeaStore(":memory:")
    yield idea_store
    idea_store.close()
