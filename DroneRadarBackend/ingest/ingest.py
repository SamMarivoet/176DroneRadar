"""
Simple ingestion CLI that reads all .json files from a folder and POSTs them to the backend /planes/bulk endpoint.
This is intentionally minimal — in production you might instead stream directly to MongoDB, use a message queue,
or implement a watch-service.
"""
