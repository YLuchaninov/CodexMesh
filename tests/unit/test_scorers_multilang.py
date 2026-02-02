"""Tests for Multi-Language Scorers."""

from codex_mesh.metrics.scorers import ConcurrencyScorer, LogicScorer, RiskScorer


def test_java_concurrency_and_risk():
    code = """
    public class AsyncRisk {
        public void run() {
            Thread t = new Thread(() -> {
                System.out.println("Async");
            });
            t.start();

            String key = System.getenv("API_KEY");
            ProcessBuilder pb = new ProcessBuilder("rm", "-rf", "/");
        }
    }
    """
    # Concurrency
    c = ConcurrencyScorer(code, "test.java").score()
    assert c.score > 0
    assert any("Thread" in i["message"] for i in c.issues)

    # Risk
    r = RiskScorer(code, "test.java").score()
    assert r.score > 0
    assert any(
        "System.getenv" in i["message"] or "ProcessBuilder" in i["message"] for i in r.issues
    )


def test_cpp_concurrency_and_risk():
    code = """
    #include <thread>
    void do_work() {
        std::thread t(worker);
        system("ls -la");
    }
    """
    c = ConcurrencyScorer(code, "test.cpp").score()
    assert c.score > 0
    assert any("std::thread" in i["message"] for i in c.issues)

    r = RiskScorer(code, "test.cpp").score()
    assert r.score > 0
    assert any("system(" in i["message"] for i in r.issues)


def test_ruby_logic():
    code = """
    def complex_method
      if condition
        case x
        when 1
          dosomething
        end
      elsif other
        unless not_true
          loop do
            break
          end
        end
      end
    end
    # Padding lines
    #
    #
    #
    #
    """
    logic_res = LogicScorer(code, "test.rb").score()
    assert logic_res.score > 0
    assert any(
        "High control flow density" in i["message"] or "Deep nesting" in i["message"]
        for i in logic_res.issues
    )
