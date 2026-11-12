"""Graph Attention Network (GAT) implemented from scratch in NumPy.

Two layers, following Velickovic et al. (2018):
  layer 1: K attention heads, ELU, heads concatenated
  layer 2: a single attention head producing class logits

Forward and backward passes are hand written (no autograd framework), so the
model trains in a few seconds on CPU and deploys anywhere (Render free tier
included). tests/test_gat.py checks every gradient against finite differences.
"""
from __future__ import annotations

import numpy as np

NEG = -1e9


def _leaky(x, slope=0.2):
    return np.where(x > 0, x, slope * x)


def _elu(x):
    return np.where(x > 0, x, np.exp(np.minimum(x, 0)) - 1)


class AttentionHead:
    """One masked self-attention head over a graph (dense mask, N up to ~2k)."""

    def __init__(self, in_dim: int, out_dim: int, rng: np.random.Generator):
        lim = np.sqrt(6 / (in_dim + out_dim))
        self.W = rng.uniform(-lim, lim, (in_dim, out_dim))
        self.a_src = rng.uniform(-0.3, 0.3, out_dim)
        self.a_dst = rng.uniform(-0.3, 0.3, out_dim)

    def params(self):
        return [self.W, self.a_src, self.a_dst]

    def forward(self, H, mask):
        Z = H @ self.W
        s = Z @ self.a_src
        d = Z @ self.a_dst
        E = s[:, None] + d[None, :]
        L = np.where(mask, _leaky(E), NEG)
        L = L - L.max(axis=1, keepdims=True)
        P = np.exp(L) * mask
        A = P / (P.sum(axis=1, keepdims=True) + 1e-12)
        out = A @ Z
        self.cache = (H, Z, E, A, mask)
        return out, A

    def backward(self, dOut):
        H, Z, E, A, mask = self.cache
        dA = dOut @ Z.T
        dZ = A.T @ dOut
        dL = A * (dA - (dA * A).sum(axis=1, keepdims=True))
        dE = dL * np.where(E > 0, 1.0, 0.2) * mask
        ds = dE.sum(axis=1)
        dd = dE.sum(axis=0)
        dZ += ds[:, None] * self.a_src[None, :] + dd[:, None] * self.a_dst[None, :]
        grads = [H.T @ dZ, Z.T @ ds, Z.T @ dd]
        dH = dZ @ self.W.T
        return dH, grads


class GAT:
    def __init__(self, in_dim, hidden=8, heads=4, n_classes=2, seed=7):
        rng = np.random.default_rng(seed)
        self.heads1 = [AttentionHead(in_dim, hidden, rng) for _ in range(heads)]
        self.head2 = AttentionHead(hidden * heads, n_classes, rng)
        self.hidden = hidden
        self.n_heads = heads
        self._adam = None
        self.history: list[dict] = []

    # ------------------------------------------------------------------ core
    def params(self):
        ps = []
        for h in self.heads1:
            ps += h.params()
        return ps + self.head2.params()

    def forward(self, X, mask):
        outs, atts = [], []
        for h in self.heads1:
            o, a = h.forward(X, mask)
            outs.append(o)
            atts.append(a)
        pre = np.concatenate(outs, axis=1)
        self._pre = pre
        H1 = _elu(pre)
        logits, a2 = self.head2.forward(H1, mask)
        self.attn1 = atts
        self.attn2 = a2
        return logits

    def backward(self, dlogits):
        dH1, g2 = self.head2.backward(dlogits)
        dpre = dH1 * np.where(self._pre > 0, 1.0, np.exp(np.minimum(self._pre, 0)))
        grads = []
        for k, h in enumerate(self.heads1):
            _, g = h.backward(dpre[:, k * self.hidden:(k + 1) * self.hidden])
            grads += g
        return grads + g2

    @staticmethod
    def softmax(logits):
        z = logits - logits.max(axis=1, keepdims=True)
        e = np.exp(z)
        return e / e.sum(axis=1, keepdims=True)

    def loss_and_grads(self, X, mask, y, train_idx, class_weight=None):
        logits = self.forward(X, mask)
        P = self.softmax(logits)
        n = len(train_idx)
        w = np.ones(n) if class_weight is None else class_weight[y[train_idx]]
        loss = -np.sum(w * np.log(P[train_idx, y[train_idx]] + 1e-12)) / n
        d = np.zeros_like(P)
        d[train_idx] = P[train_idx]
        d[train_idx, y[train_idx]] -= 1
        d[train_idx] *= w[:, None] / n
        return loss, self.backward(d), P

    # ----------------------------------------------------------------- train
    def fit(self, X, mask, y, train_idx, val_idx, epochs=120, lr=0.02, wd=5e-4):
        params = self.params()
        m = [np.zeros_like(p) for p in params]
        v = [np.zeros_like(p) for p in params]
        b1, b2 = 0.9, 0.999
        counts = np.bincount(y[train_idx], minlength=2).astype(float)
        cw = counts.sum() / (2 * np.maximum(counts, 1))
        self.history = []
        for t in range(1, epochs + 1):
            loss, grads, P = self.loss_and_grads(X, mask, y, train_idx, cw)
            for i, (p, g) in enumerate(zip(params, grads)):
                g = g + wd * p
                m[i] = b1 * m[i] + (1 - b1) * g
                v[i] = b2 * v[i] + (1 - b2) * g * g
                p -= lr * (m[i] / (1 - b1 ** t)) / (np.sqrt(v[i] / (1 - b2 ** t)) + 1e-8)
            if t % 10 == 0 or t == epochs:
                self.history.append({
                    "epoch": t,
                    "loss": round(float(loss), 4),
                    "val_auc": round(auc(y[val_idx], P[val_idx, 1]), 4),
                })
        return self.history

    def predict_proba(self, X, mask):
        return self.softmax(self.forward(X, mask))[:, 1]


def auc(y_true, score):
    y_true = np.asarray(y_true)
    pos, neg = score[y_true == 1], score[y_true == 0]
    if len(pos) == 0 or len(neg) == 0:
        return 0.5
    order = np.argsort(np.concatenate([pos, neg]))
    ranks = np.empty(len(order))
    ranks[order] = np.arange(1, len(order) + 1)
    return float((ranks[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))
