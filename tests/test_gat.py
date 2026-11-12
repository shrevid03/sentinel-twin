import numpy as np

from app.gat import GAT


def test_gradients_match_finite_differences():
    rng = np.random.default_rng(0)
    n, f = 12, 5
    X = rng.normal(size=(n, f))
    mask = (rng.random((n, n)) < 0.3) | np.eye(n, dtype=bool)
    mask = mask | mask.T
    y = rng.integers(0, 2, n)
    idx = np.arange(n)
    model = GAT(f, hidden=3, heads=2)
    _, grads, _ = model.loss_and_grads(X, mask, y, idx)
    eps = 1e-6
    for p, g in zip(model.params(), grads):
        flat = p.reshape(-1)
        for k in rng.choice(flat.size, size=min(4, flat.size), replace=False):
            old = flat[k]
            flat[k] = old + eps
            lp, _, _ = model.loss_and_grads(X, mask, y, idx)
            flat[k] = old - eps
            lm, _, _ = model.loss_and_grads(X, mask, y, idx)
            flat[k] = old
            num = (lp - lm) / (2 * eps)
            assert abs(num - g.reshape(-1)[k]) < 1e-5 + 1e-3 * abs(num)


def test_twin_trains_and_detects_rings():
    from app.twin import Twin

    twin = Twin(seed=3)
    metrics = twin.train()
    assert metrics["test_auc"] > 0.85
