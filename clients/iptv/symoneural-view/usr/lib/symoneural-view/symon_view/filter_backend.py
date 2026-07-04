"""Advanced filtering engine with regex, fuzzy matching, and caching."""

from __future__ import annotations

import logging
import re
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class FilterOperator(Enum):
    EQUALS = "eq"
    CONTAINS = "contains"
    STARTS_WITH = "startswith"
    ENDS_WITH = "endswith"
    REGEX = "regex"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    IN = "in"
    NOT_IN = "notin"
    FUZZY = "fuzzy"


@dataclass
class FilterRule:
    field: str
    operator: FilterOperator
    value: Any
    case_sensitive: bool = False
    weight: float = 1.0

    def _normalize(self, v: Any) -> Any:
        if isinstance(v, str) and not self.case_sensitive:
            return v.lower()
        return v

    def match(self, item: dict[str, Any]) -> tuple[bool, float]:
        if self.field not in item:
            return False, 0.0

        raw_item = item[self.field]
        item_value = self._normalize(raw_item)
        cmp_value = self._normalize(self.value)

        try:
            if self.operator == FilterOperator.EQUALS:
                ok = item_value == cmp_value
                score = 1.0 if ok else 0.0

            elif self.operator == FilterOperator.CONTAINS:
                ok = str(cmp_value) in str(item_value)
                score = 1.0 if ok else 0.0

            elif self.operator == FilterOperator.STARTS_WITH:
                ok = str(item_value).startswith(str(cmp_value))
                score = 1.0 if ok else 0.0

            elif self.operator == FilterOperator.ENDS_WITH:
                ok = str(item_value).endswith(str(cmp_value))
                score = 1.0 if ok else 0.0

            elif self.operator == FilterOperator.REGEX:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                ok = bool(re.search(str(self.value), str(raw_item), flags))
                score = 1.0 if ok else 0.0

            elif self.operator == FilterOperator.GREATER_THAN:
                ok = float(raw_item) > float(self.value)
                score = 1.0 if ok else 0.0

            elif self.operator == FilterOperator.LESS_THAN:
                ok = float(raw_item) < float(self.value)
                score = 1.0 if ok else 0.0

            elif self.operator == FilterOperator.IN:
                values = self.value if isinstance(self.value, list) else [self.value]
                values = [self._normalize(v) for v in values]
                ok = item_value in values
                score = 1.0 if ok else 0.0

            elif self.operator == FilterOperator.NOT_IN:
                values = self.value if isinstance(self.value, list) else [self.value]
                values = [self._normalize(v) for v in values]
                ok = item_value not in values
                score = 1.0 if ok else 0.0

            elif self.operator == FilterOperator.FUZZY:
                score = FuzzyMatcher.score(str(cmp_value), str(item_value))
                ok = score >= 0.6

            else:
                ok = False
                score = 0.0

            return ok, score * self.weight
        except Exception as e:
            logger.debug(f"Filter match error: {e}")
            return False, 0.0


class FuzzyMatcher:
    @staticmethod
    def levenshtein_ratio(s1: str, s2: str) -> float:
        if not s1 and not s2:
            return 1.0
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 1.0

        d: dict[tuple[int, int], int] = {}
        for i in range(len(s1) + 1):
            d[(i, 0)] = i
        for j in range(len(s2) + 1):
            d[(0, j)] = j

        for i in range(1, len(s1) + 1):
            for j in range(1, len(s2) + 1):
                cost = 0 if s1[i - 1] == s2[j - 1] else 1
                d[(i, j)] = min(
                    d[(i - 1, j)] + 1,
                    d[(i, j - 1)] + 1,
                    d[(i - 1, j - 1)] + cost,
                )

        distance = d[(len(s1), len(s2))]
        return 1.0 - (distance / max_len)

    @staticmethod
    def score(needle: str, haystack: str) -> float:
        needle = needle.lower().strip()
        haystack = haystack.lower().strip()

        if not needle:
            return 0.0
        if needle == haystack:
            return 1.0
        if needle in haystack:
            return 0.9
        return FuzzyMatcher.levenshtein_ratio(needle, haystack)


class FilterCache:
    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self.cache: dict[str, list[dict[str, Any]]] = {}
        self.timestamps: dict[str, float] = {}
        self.hits = 0
        self.misses = 0
        self.lock = threading.Lock()

    def get(self, key: str) -> list[dict[str, Any]] | None:
        with self.lock:
            if key in self.cache and (time.time() - self.timestamps[key]) < self.ttl:
                self.hits += 1
                return self.cache[key]
            if key in self.cache:
                del self.cache[key]
                del self.timestamps[key]
            self.misses += 1
            return None

    def set(self, key: str, value: list[dict[str, Any]]) -> None:
        with self.lock:
            self.cache[key] = value
            self.timestamps[key] = time.time()

    def invalidate(self) -> None:
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()

    def stats(self) -> dict[str, Any]:
        with self.lock:
            total = self.hits + self.misses
            return {
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": self.hits / total if total else 0.0,
                "cached_items": len(self.cache),
            }


class AdvancedFilter:
    def __init__(self, enable_cache: bool = True):
        self.rules: list[FilterRule] = []
        self.cache: FilterCache | None = FilterCache() if enable_cache else None
        self.lock = threading.RLock()
        self.stats: dict[str, Any] = {
            "filters_applied": 0,
            "items_filtered": 0,
            "avg_time": 0.0,
        }

    def add_rule(
        self,
        field: str,
        operator: FilterOperator,
        value: Any,
        case_sensitive: bool = False,
        weight: float = 1.0,
    ) -> None:
        with self.lock:
            self.rules.append(FilterRule(field, operator, value, case_sensitive, weight))
            if self.cache:
                self.cache.invalidate()

    def clear_rules(self) -> None:
        with self.lock:
            self.rules.clear()
            if self.cache:
                self.cache.invalidate()

    def _cache_key(self, combine_mode: str, score_threshold: float) -> str:
        return (
            f"{combine_mode}:{score_threshold}:"
            + "|".join(
                f"{r.field}:{r.operator.value}:{r.value}:{r.case_sensitive}:{r.weight}"
                for r in self.rules
            )
        )

    def apply(
        self,
        items: list[dict[str, Any]],
        combine_mode: str = "AND",
        score_threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        start = time.time()
        mode = combine_mode.upper()

        with self.lock:
            if not self.rules:
                return items

            key = self._cache_key(mode, score_threshold)
            if self.cache:
                cached = self.cache.get(key)
                if cached is not None:
                    return cached

            out: list[dict[str, Any]] = []
            for item in items:
                results: list[tuple[bool, float]] = [rule.match(item) for rule in self.rules]

                if mode == "AND":
                    matched = all(m for m, _ in results)
                    score = sum(s for _, s in results)
                else:  # OR
                    matched = any(m for m, _ in results)
                    score = max((s for _, s in results), default=0.0)

                if matched and score >= score_threshold:
                    row = dict(item)
                    row["_filter_score"] = score
                    out.append(row)

            out.sort(key=lambda x: x.get("_filter_score", 0.0), reverse=True)

            if self.cache:
                self.cache.set(key, out)

            self.stats["filters_applied"] += 1
            self.stats["items_filtered"] += len(items)
            n = int(self.stats["filters_applied"])
            elapsed = time.time() - start
            prev = float(self.stats["avg_time"])
            self.stats["avg_time"] = ((prev * (n - 1)) + elapsed) / n
            return out

    def get_stats(self) -> dict[str, Any]:
        info = dict(self.stats)
        if self.cache:
            info["cache"] = self.cache.stats()
        return info


class SearchEngine:
    def __init__(self):
        self.index: dict[str, list[int]] = defaultdict(list)
        self.documents: list[dict[str, Any]] = []
        self.lock = threading.RLock()

    def index_documents(self, documents: list[dict[str, Any]], fields: list[str]) -> None:
        with self.lock:
            self.documents = documents
            self.index.clear()
            for doc_id, doc in enumerate(documents):
                token_set: set[str] = set()
                for field in fields:
                    value = doc.get(field)
                    if isinstance(value, str):
                        token_set.update(self._tokenize(value))
                for token in token_set:
                    self.index[token].append(doc_id)

    def search(self, query: str, max_results: int = 50) -> list[tuple[dict[str, Any], float]]:
        with self.lock:
            q = self._tokenize(query)
            if not q:
                return []

            scores: dict[int, float] = defaultdict(float)
            for token in q:
                for doc_id in self.index.get(token, []):
                    doc = self.documents[doc_id]
                    name = str(doc.get("name", "")).lower()
                    if token in name:
                        scores[doc_id] += 10.0
                    scores[doc_id] += 1.0

            ranked = sorted(
                ((self.documents[i], s) for i, s in scores.items()),
                key=lambda x: x[1],
                reverse=True,
            )
            return ranked[:max_results]

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        text = re.sub(r"[^\w\s]", " ", text.lower())
        tokens = set(text.split())
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
        return tokens - stop_words


class FilterBuilder:
    def __init__(self):
        self.filter = AdvancedFilter()

    def name_contains(self, value: str, weight: float = 1.0) -> FilterBuilder:
        self.filter.add_rule("name", FilterOperator.CONTAINS, value, weight=weight)
        return self

    def name_regex(self, pattern: str, weight: float = 1.0) -> FilterBuilder:
        self.filter.add_rule("name", FilterOperator.REGEX, pattern, weight=weight)
        return self

    def group_in(self, groups: list[str], weight: float = 1.0) -> FilterBuilder:
        self.filter.add_rule("group", FilterOperator.IN, groups, weight=weight)
        return self

    def has_logo(self, weight: float = 1.0) -> FilterBuilder:
        self.filter.add_rule("logo", FilterOperator.NOT_IN, [None, ""], weight=weight)
        return self

    def build(self) -> AdvancedFilter:
        return self.filter
