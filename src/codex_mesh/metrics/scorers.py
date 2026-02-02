"""
Specialized scorers for Hotspot 2.0 Multi-Axis Analysis.

This module implements logic for:
- Logic/State Scoring (Complexity)
- Concurrency Scoring
- Risk/Integrations Scoring
"""

import re
from dataclasses import dataclass
from typing import Any

# Common patterns
# Regex heavily simplified for MVP

# 1. Logic/Complexity
# Keywords that suggest branching/complexity
LOGIC_KEYWORDS = {
    "python": [
        "if ",
        "elif ",
        "else:",
        "for ",
        "while ",
        "try:",
        "except ",
        "with ",
        "def ",
        "class ",
    ],
    "javascript": [
        "if",
        "else",
        "for",
        "while",
        "try",
        "catch",
        "switch",
        "case",
        "function",
        "class",
    ],
    "go": ["if", "else", "for", "switch", "select", "func", "go "],
    "rust": ["if", "else", "match", "loop", "while", "for", "fn ", "impl "],
    "java": ["if", "else", "for", "while", "switch", "try", "catch", "class ", "interface "],
    "cpp": [
        "if",
        "else",
        "for",
        "while",
        "switch",
        "try",
        "catch",
        "class ",
        "struct ",
        "template",
    ],
    "csharp": [
        "if",
        "else",
        "for",
        "foreach",
        "while",
        "switch",
        "try",
        "catch",
        "class ",
        "struct ",
    ],
    "ruby": [
        "if ",
        "else",
        "elsif",
        "unless",
        "while",
        "until",
        "case",
        "def ",
        "class ",
        "module ",
    ],
    "php": [
        "if",
        "else",
        "elseif",
        "foreach",
        "while",
        "switch",
        "try",
        "catch",
        "function ",
        "class ",
    ],
    "swift": ["if ", "else", "switch", "for ", "while ", "guard ", "func ", "class ", "struct "],
}


# 2. Concurrency
# Markers of async/threading/parallelism
CONCURRENCY_PATTERNS = [
    # Python
    r"async\s+def\s+",
    r"\s+await\s+",
    r"asyncio\.",
    r"threading\.",
    r"multiprocessing\.",
    r"concurrent\.futures",
    r"Lock\(",
    r"Semaphore\(",
    r"Queue\(",
    # JS/TS
    r"async\s+function",
    r"\s+await\s+",
    r"Promise",
    r"setTimeout",
    # Go
    r"go\s+\w+",
    r"chan\s+",
    r"select\s+\{",
    r"sync\.Mutex",
    r"sync\.WaitGroup",
    # Java
    r"Thread",
    r"Runnable",
    r"CompletableFuture",
    r"synchronized",
    r"ExecutorService",
    # C++
    r"std::thread",
    r"std::async",
    r"std::mutex",
    r"std::future",
    # C#
    r"Task\.Run",
    r"Task<",
    r"await\s+",
    r"Thread\.",
    r"lock\s*\(",
    # Swift
    r"Task\s*\{",
    r"await\s+",
    r"actor\s+",
    r"DispatchQueue",
    # Ruby
    r"Thread\.new",
    r"Mutex\.new",
    # PHP
    r"pthreads",
    r"Worker",
]


# 3. Risk / Integrations
# Markers of IO / External calls / Env vars / Dangerous ops
RISK_PATTERNS = [
    # Env vars
    r"os\.environ",
    r"os\.getenv",
    r"process\.env",
    r"std::env",
    r"System\.getenv",
    r"Environment\.GetEnvironmentVariable",
    r"ENV\[",
    r"\$_ENV",
    # Network / DB (Heuristic by popular libs)
    r"requests\.",
    r"httpx\.",
    r"boto3\.",
    r"sqlalchemy\.",
    r"psycopg2",
    r"redis\.",
    r"pymongo",
    r"fetch\(",
    r"axios\.",
    r"http\.Get",
    r"http\.Post",
    r"database/sql",
    # Java/C# Risk
    r"java\.net",
    r"HttpClient",
    r"ProcessBuilder",
    r"Process\.Start",
    r"Runtime\.exec",
    # C++
    r"system\(",
    r"popen\(",
    # Ruby/PHP
    r"Net::HTTP",
    r"curl_",
    r"shell_exec",
    r"\$_GET",
    r"\$_POST",
    # Swift
    r"URLSession",
    # dangerous
    r"eval\(",
    r"exec\(",
    r"subprocess\.",
    r"os\.system",
]


@dataclass
class ScorerResult:
    score: float
    issues: list[dict[str, Any]]


class BaseScorer:
    def __init__(self, content: str, file_path: str):
        self.content = content
        self.file_path = file_path.lower()
        self.lines = content.splitlines()

    def score(self) -> ScorerResult:
        raise NotImplementedError

    def _iter_code_lines(self):
        """
        Yield lines with (most) comments stripped / skipped.
        Goal: avoid scoring on TODOs / keywords / secrets that appear only in comments.
        This is intentionally heuristic (fast + robust) and not a full parser.
        """
        fp = self.file_path

        # Determine comment syntax by extension
        hash_comment = fp.endswith(
            (".py", ".rb", ".sh", ".bash", ".zsh", ".yaml", ".yml", ".toml", ".ini", ".cfg")
        )
        sql_comment = fp.endswith((".sql",))
        c_like = fp.endswith(
            (
                ".js",
                ".ts",
                ".jsx",
                ".tsx",
                ".java",
                ".c",
                ".cc",
                ".cpp",
                ".h",
                ".hpp",
                ".cs",
                ".go",
                ".rs",
                ".swift",
                ".php",
                ".kt",
                ".kts",
            )
        )

        line_prefixes = []
        block_comments = False

        if hash_comment:
            line_prefixes = ["#"]
        elif sql_comment:
            line_prefixes = ["--"]
        elif c_like:
            line_prefixes = ["//"]
            block_comments = True
        else:
            # fallback (safe default)
            line_prefixes = ["#", "//"]
            block_comments = True

        in_block = False

        for raw in self.lines:
            line = raw

            # Handle block comments (/* ... */)
            if block_comments:
                if in_block:
                    if "*/" in line:
                        _, after = line.split("*/", 1)
                        line = after
                        in_block = False
                    else:
                        continue

                while "/*" in line:
                    before, rest = line.split("/*", 1)
                    if "*/" in rest:
                        after = rest.split("*/", 1)[1]
                        line = before + " " + after
                    else:
                        line = before
                        in_block = True
                        break

            stripped = line.lstrip()
            if not stripped:
                continue

            # Skip full-line comments
            if any(stripped.startswith(p) for p in line_prefixes):
                continue

            # Strip inline line comments (heuristic)
            for p in line_prefixes:
                pos = line.find(p)
                if pos != -1:
                    line = line[:pos]
                    break

            if line.strip():
                yield line


class LogicScorer(BaseScorer):
    """
    Scores complexity based on indentation, length, and keywords.
    """

    def score(self) -> ScorerResult:
        issues = []
        total_score = 0.0

        # 1. Length penalty
        # > 300 lines starts adding score
        line_count = len(self.lines)
        if line_count > 300:
            s = (line_count - 300) / 100.0  # +1 per 100 extra lines
            total_score += s
            issues.append(
                {"type": "logic", "message": f"High line count ({line_count})", "weight": s}
            )

        # 2. Indentation depth (proxy for nesting)
        max_depth = 0
        deep_lines = 0
        for line in self.lines:
            stripped = line.lstrip()
            if not stripped or stripped.startswith(("#", "//")):
                continue

            # Simple 4-space indent assumption
            indent = len(line) - len(stripped)
            depth = indent // 4
            max_depth = max(max_depth, depth)

            if depth > 4:
                deep_lines += 1

        if max_depth > 5:
            s = (max_depth - 4) * 0.5
            total_score += s
            issues.append(
                {"type": "logic", "message": f"Deep nesting (max depth {max_depth})", "weight": s}
            )

        if deep_lines > 10:
            s = deep_lines * 0.1
            total_score += s
            issues.append(
                {
                    "type": "logic",
                    "message": f"Frequent deep nesting ({deep_lines} lines > depth 4)",
                    "weight": s,
                }
            )

        # 3. Keywords heuristic
        # Try to detect language or fallback
        lang_keywords = LOGIC_KEYWORDS.get("python", [])  # default to pythonish
        if self.file_path.endswith((".js", ".ts", ".jsx", ".tsx")):
            lang_keywords = LOGIC_KEYWORDS["javascript"]
        elif self.file_path.endswith(".go"):
            lang_keywords = LOGIC_KEYWORDS["go"]
        elif self.file_path.endswith(".rs"):
            lang_keywords = LOGIC_KEYWORDS["rust"]
        elif self.file_path.endswith(".java"):
            lang_keywords = LOGIC_KEYWORDS["java"]
        elif self.file_path.endswith((".c", ".cc", ".cpp", ".h", ".hpp", ".cxx")):
            lang_keywords = LOGIC_KEYWORDS["cpp"]
        elif self.file_path.endswith(".cs"):
            lang_keywords = LOGIC_KEYWORDS["csharp"]
        elif self.file_path.endswith(".rb"):
            lang_keywords = LOGIC_KEYWORDS["ruby"]
        elif self.file_path.endswith(".php"):
            lang_keywords = LOGIC_KEYWORDS["php"]
        elif self.file_path.endswith(".swift"):
            lang_keywords = LOGIC_KEYWORDS["swift"]

        complexity_count = 0
        for line in self._iter_code_lines():
            stripped = line.strip()
            for kw in lang_keywords:
                if kw in stripped:
                    complexity_count += 1

        # Density check: > 10% of lines are control flow -> complex
        # Only for files with sufficient length to matter (>10 lines)
        if line_count > 10:
            density = complexity_count / line_count
            if density > 0.15:  # 15% is fairly dense logic
                s = (density - 0.15) * 20.0  # moderate penalty
                total_score += s
                issues.append(
                    {
                        "type": "logic",
                        "message": f"High control flow density ({density:.1%})",
                        "weight": s,
                    }
                )

        return ScorerResult(total_score, issues)


class ConcurrencyScorer(BaseScorer):
    """
    Scores concurrency risk based on regex patterns.
    """

    def __init__(self, content: str, file_path: str):
        super().__init__(content, file_path)
        self.regexes = [re.compile(p) for p in CONCURRENCY_PATTERNS]

    def score(self) -> ScorerResult:
        issues = []
        total_score = 0.0

        hits = 0
        unique_matches = set()

        for line in self._iter_code_lines():
            for regex in self.regexes:
                match = regex.search(line)
                if match:
                    hits += 1
                    unique_matches.add(match.group(0).strip())

        if hits > 0:
            # Base score for having ANY concurrency
            total_score += 1.0

            # Additional score for volume
            vol_score = hits * 0.1
            total_score += vol_score

            issues.append(
                {
                    "type": "concurrency",
                    "message": f"Concurrency markers detected: {', '.join(list(unique_matches)[:5])}",
                    "weight": 1.0 + vol_score,
                }
            )

        return ScorerResult(total_score, issues)


class RiskScorer(BaseScorer):
    """
    Scores integration/ops risk based on regex patterns.
    """

    def __init__(self, content: str, file_path: str):
        super().__init__(content, file_path)
        self.regexes = [re.compile(p) for p in RISK_PATTERNS]

    def score(self) -> ScorerResult:
        issues = []
        total_score = 0.0

        hits = 0
        unique_matches = set()

        for line in self._iter_code_lines():
            for regex in self.regexes:
                match = regex.search(line)
                if match:
                    hits += 1
                    unique_matches.add(match.group(0).strip())

        if hits > 0:
            # Base score for having ANY risk/integration
            total_score += 0.5

            # Additional score for volume
            vol_score = hits * 0.2
            total_score += vol_score

            issues.append(
                {
                    "type": "risk",
                    "message": f"Risk/Integration markers: {', '.join(list(unique_matches)[:5])}",
                    "weight": 0.5 + vol_score,
                }
            )

        return ScorerResult(total_score, issues)
