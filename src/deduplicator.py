"""
Content-based deduplication using SimHash.
"""
import re
import hashlib
from collections import OrderedDict
from typing import List, Tuple


class SimHash:
    """Simple SimHash implementation for near-duplicate detection."""

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Tokenize text into words (lowercase, remove punctuation)."""
        text = re.sub(r'<[^>]+>', '', text)  # strip HTML tags
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        return text.split()

    @staticmethod
    def _hash_token(token: str) -> int:
        """Hash a token to a 64-bit integer."""
        return int(hashlib.md5(token.encode()).hexdigest()[:16], 16)

    @staticmethod
    def compute(text: str) -> int:
        """Compute SimHash fingerprint for text."""
        tokens = SimHash._tokenize(text)
        if not tokens:
            return 0

        v = [0] * 64
        for token in tokens:
            h = SimHash._hash_token(token)
            for i in range(64):
                if h & (1 << i):
                    v[i] += 1
                else:
                    v[i] -= 1

        fingerprint = 0
        for i in range(64):
            if v[i] > 0:
                fingerprint |= (1 << i)
        return fingerprint

    @staticmethod
    def hamming_distance(a: int, b: int) -> int:
        """Calculate Hamming distance between two fingerprints."""
        x = a ^ b
        return bin(x).count('1')


class Deduplicator:
    """
    Content deduplicator with FIFO buffer.
    Detects exact and near-duplicate news items.
    """

    def __init__(self, max_items: int = 500, short_text_threshold: int = 200,
                 short_distance: int = 3, long_distance: int = 5):
        self.max_items = max_items
        self.short_text_threshold = short_text_threshold
        self.short_distance = short_distance
        self.long_distance = long_distance
        self.fingerprints = OrderedDict()  # url -> fingerprint
        self.stats = {
            "total_processed": 0,
            "duplicates_found": 0
        }

    def is_duplicate(self, text: str, url: str = None) -> Tuple[bool, str]:
        """
        Check if text is duplicate of any previously seen.
        Returns (is_dup, matched_url).
        """
        if not text:
            return False, ""

        fp = SimHash.compute(text)
        text_len = len(text)
        threshold = self.short_distance if text_len < self.short_text_threshold else self.long_distance

        for existing_url, existing_fp in self.fingerprints.items():
            if SimHash.hamming_distance(fp, existing_fp) <= threshold:
                self.stats["duplicates_found"] += 1
                return True, existing_url

        # Not a duplicate, add to buffer
        self._add(url if url else str(hash(text)), fp)
        return False, ""

    def _add(self, url: str, fingerprint: int):
        """Add fingerprint to FIFO buffer, evicting oldest if necessary."""
        if len(self.fingerprints) >= self.max_items:
            self.fingerprints.popitem(last=False)
        self.fingerprints[url] = fingerprint
        self.stats["total_processed"] += 1

    def is_url_processed(self, url: str) -> bool:
        """Check if URL is already in the buffer."""
        return url in self.fingerprints

    def mark_url_processed(self, url: str, text: str):
        """Force-add a URL with its fingerprint."""
        fp = SimHash.compute(text)
        self._add(url, fp)

    def get_stats(self) -> dict:
        """Return duplicate statistics."""
        total = self.stats["total_processed"]
        dup = self.stats["duplicates_found"]
        return {
            "total_processed": total,
            "duplicates_found": dup,
            "duplicate_ratio": dup / total if total > 0 else 0.0
        }

    def reset(self):
        """Clear all fingerprints and stats."""
        self.fingerprints.clear()
        self.stats = {"total_processed": 0, "duplicates_found": 0}