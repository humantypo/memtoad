import hashlib
import re

from chromadb.api.types import EmbeddingFunction


class StubEmbedding(EmbeddingFunction):
    """Deterministic bag-of-words vectors; counts texts embedded so tests can prove idempotence."""

    def __init__(self, dims=64, label="memstore-stub"):
        self.dims, self.label, self.embedded = dims, label, 0

    def __call__(self, input):
        out = []
        for text in input:
            self.embedded += 1
            vec = [0.0] * self.dims
            for word in re.findall(r"[a-z0-9]+", text.lower()):
                vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dims] += 1.0
            norm = sum(v * v for v in vec) ** 0.5 or 1.0
            out.append([v / norm for v in vec])
        return out

    def name(self):
        return self.label

    def get_config(self):
        return {"dims": self.dims, "label": self.label}

    @staticmethod
    def build_from_config(config):
        return StubEmbedding(**config)

    def default_space(self):
        return "cosine"

    def supported_spaces(self):
        return ["cosine", "l2", "ip"]


def tree_hashes(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.rglob("*")) if p.is_file()}
