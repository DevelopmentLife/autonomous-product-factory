import re
import math


SECRET_PATTERNS = [
    re.compile(r'(?i)(api[_-]?key|secret[_-]?key|access[_-]?token)\s*[=:]\s*["\'][^"\']{16,}'),
    re.compile(r'sk-[a-zA-Z0-9]{48}'),
    re.compile(r'sk-ant-[a-zA-Z0-9\-]{32,}'),
    re.compile(r'AKIA[0-9A-Z]{16}'),
]
ENTROPY_THRESHOLD = 4.5


def _entropy(s: str) -> float:
    if not s:
        return 0.0
    freq = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    length = len(s)
    return -sum((f / length) * math.log2(f / length) for f in freq.values())


def scan_for_secrets(content: str) -> list[dict]:
    findings = []
    for pattern in SECRET_PATTERNS:
        for match in pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            findings.append({
                'type': 'pattern_match',
                'match': match.group(0)[:30] + '...',
                'line': line_num,
            })
    for word in content.split():
        if len(word) >= 20 and _entropy(word) > ENTROPY_THRESHOLD:
            findings.append({'type': 'high_entropy', 'value': word[:10] + '...'})
    return findings
