# test_qdrant.py
from qdrant_client import QdrantClient
client = QdrantClient(url="http://localhost:6333")
print(dir(client)) # This will literally list everything the client can do