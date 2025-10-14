# indexing_algos.py
import bisect
from collections import defaultdict, deque

class LinearSearch:
    """Baseline linear scan over rows (list of dicts)."""
    def __init__(self, rows):
        self.rows = rows

    def exact_name(self, name):
        return [r for r in self.rows if r.get("name") == name]

    def range_age(self, a, b):
        return [r for r in self.rows if r.get("age") is not None and a <= r["age"] <= b]

    def prefix_name(self, prefix):
        return [r for r in self.rows if r.get("name", "").startswith(prefix)]

class HashIndex:
    """Hash index for exact-match queries on a given key (default 'name')."""
    def __init__(self, rows, key="name"):
        self.key = key
        self.idx = defaultdict(list)
        for r in rows:
            v = r.get(key)
            if v is not None:
                self.idx[v].append(r)

    def exact_name(self, value):
        return list(self.idx.get(value, []))

class BinaryIndex:
    """Binary index for numeric range queries (e.g., age)."""
    def __init__(self, rows, key="age"):
        self.key = key
        # filter out rows where key is None to avoid comparison errors
        self.sorted = sorted((r for r in rows if r.get(key) is not None), key=lambda r: r[key])
        self.keys = [r[key] for r in self.sorted]

    def range_age(self, lo, hi):
        l = bisect.bisect_left(self.keys, lo)
        r = bisect.bisect_right(self.keys, hi)
        return self.sorted[l:r]

class TrieNode:
    def __init__(self):
        self.c = {}
        self.out = []

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, key, payload):
        cur = self.root
        for ch in key:
            if ch not in cur.c:
                cur.c[ch] = TrieNode()
            cur = cur.c[ch]
        cur.out.append(payload)

    def starts_with(self, prefix):
        cur = self.root
        for ch in prefix:
            if ch not in cur.c:
                return []
            cur = cur.c[ch]
        # collect subtree outputs
        res = []
        dq = deque([cur])
        while dq:
            node = dq.popleft()
            res.extend(node.out)
            for v in node.c.values():
                dq.append(v)
        return res

def build_trie(rows):
    t = Trie()
    for r in rows:
        name = r.get("name")
        if name:
            t.insert(name, r)
    return t
