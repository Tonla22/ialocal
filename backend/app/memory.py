"""Memory boundary: chat history lives in database.messages; working tool context
is held only for the current run; explicit persistent notes live in memories.
A future semantic retriever can implement this protocol without changing tools.
"""
from typing import Protocol

class MemoryRetriever(Protocol):
    def search(self, query: str, limit: int = 5) -> list[str]: ...
