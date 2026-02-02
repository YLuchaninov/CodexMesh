"""Tests for Multi-Axis Scorers (P2)."""

from codex_mesh.metrics.scorers import ConcurrencyScorer, LogicScorer, RiskScorer


def test_logic_scorer_simple():
    code = "def foo():\n    return 1"
    res = LogicScorer(code, "test.py").score()
    # Should be low score
    assert res.score < 0.2
    assert len(res.issues) == 0


def test_logic_scorer_nesting():
    # 6 levels of indentation (assuming 4 spaces)
    code = """
def deep():
    if a:
        if b:
            if c:
                if d:
                    if e:
                        print("too deep")
"""
    res = LogicScorer(code, "test.py").score()
    assert res.score > 0
    assert any("Deep nesting" in i["message"] for i in res.issues)


def test_logic_scorer_keywords():
    # Dense control flow
    code = """
    if a:
        for x in y:
            while z:
                try:
                    pass
                except:
                    pass
        # Padding to pass line count check (>10)
        #
        #
        #
        #
        """
    res = LogicScorer(code, "test.py").score()
    # Density is high here
    assert any("High control flow density" in i["message"] for i in res.issues)


def test_concurrency_scorer_python():
    code = """
import asyncio

async def main():
    await asyncio.sleep(1)
"""
    res = ConcurrencyScorer(code, "test.py").score()
    assert res.score > 1.0  # Base 1.0 + volume
    assert any("async def" in i["message"] for i in res.issues)


def test_concurrency_scorer_go():
    code = """
func main() {
    go doSomething()
    c := make(chan int)
    select {
    case <-c:
    }
}
"""
    res = ConcurrencyScorer(code, "test.go").score()
    assert res.score > 1.0
    assert any("go " in i["message"] or "chan " in i["message"] for i in res.issues)


def test_risk_scorer_env_and_net():
    code = """
import os
import requests

key = os.environ['API_KEY']
requests.get('https://example.com')
"""
    res = RiskScorer(code, "test.py").score()
    assert res.score > 0.5
    assert any("os.environ" in i["message"] for i in res.issues)
    assert any("requests." in i["message"] for i in res.issues)


def test_risk_scorer_safe_code():
    code = "print('hello')"
    res = RiskScorer(code, "test.py").score()
    assert res.score == 0.0
    assert len(res.issues) == 0
