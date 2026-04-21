"""
Phase 5.2 — Sustainability scoring (MVP)
========================================
Heuristic scoring (0–100) without external dependencies.
"""

from __future__ import annotations


def sustainability_score(product: dict) -> dict:
    name = str(product.get("name") or "").lower()
    desc = str(product.get("description") or "").lower()
    text = f"{name} {desc}"

    score = 55
    reasons: list[str] = []

    # Simple material heuristics
    if any(k in text for k in ("bamboo", "recycled", "fsc", "renewable", "solid wood")):
        score += 18
        reasons.append("renewable/recycled materials mentioned")
    if any(k in text for k in ("plastic", "polyester", "laminate")):
        score -= 10
        reasons.append("higher-impact materials mentioned")
    if any(k in text for k in ("led", "energy", "efficient")):
        score += 6
        reasons.append("energy-efficiency hint")

    # Durability proxy: weight + price correlate loosely with longevity; keep small influence.
    price = product.get("price") or product.get("price_usd") or product.get("price_low")
    try:
        p = float(price)
        if p > 400:
            score += 5
            reasons.append("higher price proxy for durability")
        elif p < 50:
            score -= 3
            reasons.append("low price proxy for shorter lifespan")
    except Exception:
        pass

    score = max(0, min(100, int(round(score))))
    return {"score": score, "reasons": reasons}

