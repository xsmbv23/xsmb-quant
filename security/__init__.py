"""Fosennic communication security primitives.

Runtime boundary enforcement lives here. Keep this package dependency-light:
security must sit below application orchestration and must not depend on UI,
network crawlers, or promotion code.
"""

from .corridor import Corridor, CorridorGate, DenyReason, Layer, MessageEnvelope, Room

__all__ = ["Corridor", "CorridorGate", "DenyReason", "Layer", "MessageEnvelope", "Room"]
