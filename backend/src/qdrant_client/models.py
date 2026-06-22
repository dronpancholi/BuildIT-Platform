"""Stub models for qdrant_client used in tests.
Only minimal structures are defined to satisfy attribute accesses.
"""

from __future__ import annotations

class Distance:
    COSINE = "COSINE"

class VectorParams:
    def __init__(self, size: int, distance):
        self.size = size
        self.distance = distance

class PointStruct:
    def __init__(self, id, vector, payload):
        self.id = id
        self.vector = vector
        self.payload = payload

class MatchValue:
    def __init__(self, value):
        self.value = value

class FieldCondition:
    def __init__(self, key, match):
        self.key = key
        self.match = match

class Filter:
    def __init__(self, must):
        self.must = must
