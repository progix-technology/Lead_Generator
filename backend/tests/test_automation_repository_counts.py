import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio

from app.repositories.automation import AutomationRepository


class DummyCollection:
    def __init__(self, docs):
        self.docs = docs

    async def count_documents(self, query=None):
        if not query:
            return len(self.docs)
        status = query.get("status")
        if status is None:
            return len(self.docs)
        return sum(1 for doc in self.docs if doc.get("status") == status)


class DummyDB:
    def __init__(self, records):
        self.records = records
        self._collections = {}
        self._collections["automation_settings"] = DummyCollection([])
        self._collections["automation_records"] = DummyCollection(records)
        self._collections["companies"] = DummyCollection([])

    def __getitem__(self, name):
        return self._collections[name]


def test_count_records_counts_only_sent_status():
    records = [
        {"status": "Pending_Email"},
        {"status": "Sent"},
        {"status": "Sent"},
        {"status": "Failed"},
    ]
    repo = AutomationRepository(DummyDB(records))

    total = asyncio.run(repo.count_records())

    assert total == 2
