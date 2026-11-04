"""Index logged attacker commands into the vector database.

Usage:  python index_logs.py
"""
from vector_store import index_events

result = index_events()
print(f"Backend   : {result['backend']}")
print(f"Embeddings: {result['mode']}")
print(f"New       : {result['new']}")
print(f"Total     : {result['total']}")