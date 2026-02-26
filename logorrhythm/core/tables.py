"""Deterministic session tables."""

from __future__ import annotations

from collections import OrderedDict


class NameTable:
    def __init__(self, mapping: dict[str, int]):
        self.name_to_id = dict(mapping)
        self.id_to_name = {v: k for k, v in mapping.items()}


class ValueTable:
    def __init__(self, max_entries: int = 4096, learning_threshold: int = 2):
        self.max_entries = max_entries
        self.learning_threshold = learning_threshold
        self.value_to_id: dict[object, int] = {}
        self.id_to_value: dict[int, object] = {}
        self._lru = OrderedDict()
        self._seen: dict[object, int] = {}
        self._next_id = 1


    def preload(self, values: list[object]) -> None:
        """Preload known common literals with stable IDs for this session."""
        for value in values:
            if value in self.value_to_id:
                self._touch(value)
                continue
            vid = self._next_id
            self._next_id += 1
            self.value_to_id[value] = vid
            self.id_to_value[vid] = value
            self._touch(value)
        self._evict_if_needed()

    def maybe_learn(self, value: object, allow: bool = True) -> int | None:
        if not self._is_hashable(value):
            return None
        if value in self.value_to_id:
            vid = self.value_to_id[value]
            self._touch(value)
            return vid
        if not allow:
            return None
        cnt = self._seen.get(value, 0) + 1
        self._seen[value] = cnt
        if cnt < self.learning_threshold:
            return None
        vid = self._next_id
        self._next_id += 1
        self.value_to_id[value] = vid
        self.id_to_value[vid] = value
        self._touch(value)
        self._evict_if_needed()
        return vid

    def get_id(self, value: object) -> int | None:
        if not self._is_hashable(value):
            return None
        vid = self.value_to_id.get(value)
        if vid is not None:
            self._touch(value)
        return vid

    def get_value(self, value_id: int) -> object:
        value = self.id_to_value[value_id]
        self._touch(value)
        return value

    def _touch(self, value: object) -> None:
        self._lru[value] = None
        self._lru.move_to_end(value)

    @staticmethod
    def _is_hashable(value: object) -> bool:
        try:
            hash(value)
        except TypeError:
            return False
        return True

    def _evict_if_needed(self) -> None:
        while len(self.value_to_id) > self.max_entries:
            value, _ = self._lru.popitem(last=False)
            vid = self.value_to_id.pop(value)
            self.id_to_value.pop(vid, None)

    def reset(self) -> None:
        self.value_to_id.clear()
        self.id_to_value.clear()
        self._lru.clear()
        self._seen.clear()
        self._next_id = 1
