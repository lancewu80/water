"""
checker.py
----------
Static-analysis rule engines for 8 TOGAF software-development principles.

Each principle is represented as a Check dataclass (id, name, priority, findings).
A Finding describes one violation: file, line, evidence text, severity.

Usage (standalone test):
    python checker.py D:/myproject
"""

from __future__ import annotations

import re
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from principles_config import get_spec

# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class Finding:
    filepath: str
    line_no: int          # 0 = file-level (no specific line)
    evidence: str         # short snippet or description
    severity: str         # HIGH | MEDIUM | LOW
    rule: str             # short rule description


@dataclass
class PrincipleResult:
    principle_id: str     # e.g. "P15"
    principle_name: str
    priority: str         # 最高 | 高
    findings: List[Finding] = field(default_factory=list)
    passed: bool = True   # turns False as soon as a HIGH/MEDIUM finding is added
    checks_run: int = 0   # total individual checks performed
    checks_passed: int = 0

    def add_finding(self, finding: Finding):
        self.findings.append(finding)
        if finding.severity in ('HIGH', 'MEDIUM'):
            self.passed = False

    @property
    def score(self) -> int:
        """0-100 compliance score."""
        if self.checks_run == 0:
            return 100
        return round(self.checks_passed / self.checks_run * 100)


@dataclass
class ProjectCheckResult:
    root: str
    results: List[PrincipleResult] = field(default_factory=list)
    total_files_scanned: int = 0
    generated_at: str = ""


# ── File reader ───────────────────────────────────────────────────────────────

def _read(filepath: Path) -> str:
    for enc in ('utf-8', 'cp950', 'big5', 'latin-1'):
        try:
            return filepath.read_text(encoding=enc)
        except Exception:
            continue
    return ""


def _lines(content: str) -> List[Tuple[int, str]]:
    """Return (1-based line_no, line) pairs."""
    return list(enumerate(content.splitlines(), start=1))


# ── Skip helpers (reuse same logic as analyzer) ───────────────────────────────

SKIP_DIRS = {
    '.git', '.claude', 'target', 'build', '__pycache__',
    'node_modules', '.tmp_ccms', 'update', 'archive',
}
COPY_FOLDER_MARKERS = ('ciopy', ' - copy', '-copy', '_copy', '複製', 'backup', 'bak')


def _skip(path: Path, root: Path) -> bool:
    if path.is_relative_to(root):
        parts = path.relative_to(root).parts
    else:
        parts = path.parts
    for part in parts:
        if part in SKIP_DIRS:
            return True
        pl = part.lower()
        if any(m in pl for m in COPY_FOLDER_MARKERS):
            return True
    return False


# ── File collectors ───────────────────────────────────────────────────────────

def _collect(root: Path, suffix: str) -> List[Path]:
    return [p for p in sorted(root.rglob(f'*{suffix}')) if not _skip(p, root)]


# ══════════════════════════════════════════════════════════════════════════════
# P15 – Data Security
# 加密、認證、授權、防注入攻擊
# ══════════════════════════════════════════════════════════════════════════════

_HARDCODED_PW = re.compile(
    r'(?:password|passwd|pwd|secret|token)\s*=\s*"[^"]{3,}"',
    re.IGNORECASE
)
_SQL_CONCAT = re.compile(
    r'(?:SELECT|INSERT|UPDATE|DELETE|FROM|WHERE).*\+\s*\w+',
    re.IGNORECASE
)
_TOKEN_FALSE = re.compile(r'isTokenRequired\s*=\s*["\']?false["\']?', re.IGNORECASE)
_CORS_WILDCARD = re.compile(r'Access-Control-Allow-Origin["\s:,]+\*')
_AUTH_ANNOT = re.compile(r'@(?:Secured|PreAuthorize|RolesAllowed|RequiresPermissions)', re.IGNORECASE)
_ENCRYPT_USAGE = re.compile(r'(?:AES|RSA|SHA|BCrypt|MessageDigest|Cipher|encrypt|decrypt)', re.IGNORECASE)


def check_p15(root: Path) -> PrincipleResult:
    _s = get_spec('P15')
    result = PrincipleResult(_s.id, _s.name, _s.priority)

    java_files = _collect(root, '.java')
    jsp_files  = _collect(root, '.jsp')
    all_files  = java_files + jsp_files

    has_auth   = False
    has_crypto = False

    for fp in all_files:
        content = _read(fp)
        if not content:
            continue
        rel = str(fp.relative_to(root))
        lvs = _lines(content)

        # Rule 1: hardcoded credentials
        for ln, line in lvs:
            result.checks_run += 1
            if _HARDCODED_PW.search(line) and '//' not in line.split(_HARDCODED_PW.pattern)[0][-3:]:
                result.add_finding(Finding(rel, ln, line.strip()[:120], 'HIGH',
                                           '硬編碼密碼/金鑰'))
            else:
                result.checks_passed += 1

        # Rule 2: SQL injection (string concatenation in SQL)
        for ln, line in lvs:
            result.checks_run += 1
            if _SQL_CONCAT.search(line):
                result.add_finding(Finding(rel, ln, line.strip()[:120], 'HIGH',
                                           'SQL 字串拼接（潛在注入風險）'))
            else:
                result.checks_passed += 1

        # Rule 3: token bypass
        for ln, line in lvs:
            result.checks_run += 1
            if _TOKEN_FALSE.search(line):
                result.add_finding(Finding(rel, ln, line.strip()[:120], 'HIGH',
                                           'isTokenRequired=false 跳過認證'))
            else:
                result.checks_passed += 1

        # Rule 4: CORS wildcard
        for ln, line in lvs:
            result.checks_run += 1
            if _CORS_WILDCARD.search(line):
                result.add_finding(Finding(rel, ln, line.strip()[:120], 'MEDIUM',
                                           'CORS 開放通配符 (*)'))
            else:
                result.checks_passed += 1

        # File-level: auth annotation presence
        if _AUTH_ANNOT.search(content):
            has_auth = True
        if _ENCRYPT_USAGE.search(content):
            has_crypto = True

    # Rule 5: no auth annotation anywhere
    result.checks_run += 1
    if has_auth:
        result.checks_passed += 1
    else:
        result.add_finding(Finding('(全域)', 0,
                                   '未發現 @Secured / @PreAuthorize 等授權標記',
                                   'MEDIUM', '缺少授權框架'))

    # Rule 6: no encryption usage
    result.checks_run += 1
    if has_crypto:
        result.checks_passed += 1
    else:
        result.add_finding(Finding('(全域)', 0,
                                   '未發現加密/雜湊 API 使用',
                                   'MEDIUM', '缺少加密實作'))

    return result


# ══════════════════════════════════════════════════════════════════════════════
# P16 – Technology Independence
# 抽象層、依賴注入、避免 Vendor Lock-in
# ══════════════════════════════════════════════════════════════════════════════

_DIRECT_IMPL = re.compile(r'new\s+\w*(?:Impl|DAO|Dao|ServiceImpl)\s*\(', re.IGNORECASE)
_INTERFACE_DECL = re.compile(r'\binterface\s+\w+')
_CLASS_DECL = re.compile(r'\bclass\s+\w+')
_DI_ANNOTATIONS = re.compile(r'@(?:Autowired|Inject|Resource|Component|Service|Repository)', re.IGNORECASE)
_VENDOR_LOCK = re.compile(
    r'(?:com\.mysql|oracle\.jdbc|com\.microsoft\.sqlserver|'
    r'com\.ibm\.db2|net\.sf\.json|org\.json\.simple)',
    re.IGNORECASE
)


def check_p16(root: Path) -> PrincipleResult:
    _s = get_spec('P16')
    result = PrincipleResult(_s.id, _s.name, _s.priority)

    java_files = _collect(root, '.java')
    interface_count = 0
    class_count = 0
    has_di = False

    for fp in java_files:
        content = _read(fp)
        if not content:
            continue
        rel = str(fp.relative_to(root))
        lvs = _lines(content)

        if _INTERFACE_DECL.search(content):
            interface_count += 1
        if _CLASS_DECL.search(content):
            class_count += 1
        if _DI_ANNOTATIONS.search(content):
            has_di = True

        # Rule 1: direct new *Impl() — bypasses abstraction
        for ln, line in lvs:
            result.checks_run += 1
            if _DIRECT_IMPL.search(line) and not line.strip().startswith('//'):
                result.add_finding(Finding(rel, ln, line.strip()[:120], 'MEDIUM',
                                           '直接 new *Impl() 破壞抽象層'))
            else:
                result.checks_passed += 1

        # Rule 2: vendor-specific imports
        for ln, line in lvs:
            result.checks_run += 1
            if _VENDOR_LOCK.search(line) and 'import' in line:
                result.add_finding(Finding(rel, ln, line.strip()[:120], 'MEDIUM',
                                           '直接依賴廠商特定類別（Vendor Lock-in）'))
            else:
                result.checks_passed += 1

    # Rule 3: interface-to-class ratio (should have interfaces)
    result.checks_run += 1
    if class_count > 0 and interface_count / max(class_count, 1) >= 0.15:
        result.checks_passed += 1
    elif class_count > 0:
        ratio = f"{interface_count}/{class_count}"
        result.add_finding(Finding('(全域)', 0,
                                   f'Interface 比例過低：{ratio}（建議 ≥15%）',
                                   'MEDIUM', '缺乏抽象介面'))

    # Rule 4: dependency injection presence
    result.checks_run += 1
    if has_di:
        result.checks_passed += 1
    else:
        result.add_finding(Finding('(全域)', 0,
                                   '未發現依賴注入標記 (@Autowired/@Inject)',
                                   'LOW', '缺少依賴注入'))

    return result


# ══════════════════════════════════════════════════════════════════════════════
# P20 – Control Technical Diversity
# 統一技術棧、遵守語言/框架規範
# ══════════════════════════════════════════════════════════════════════════════

_JSON_LIBS = {
    'jackson':  re.compile(r'com\.fasterxml\.jackson', re.IGNORECASE),
    'gson':     re.compile(r'com\.google\.gson', re.IGNORECASE),
    'fastjson': re.compile(r'com\.alibaba\.fastjson', re.IGNORECASE),
    'json-simple': re.compile(r'org\.json\.simple', re.IGNORECASE),
    'org.json': re.compile(r'org\.json\.JSONObject', re.IGNORECASE),
    'net.sf.json': re.compile(r'net\.sf\.json', re.IGNORECASE),
}
_LOG_LIBS = {
    'log4j':    re.compile(r'org\.apache\.log4j', re.IGNORECASE),
    'logback':  re.compile(r'ch\.qos\.logback', re.IGNORECASE),
    'slf4j':    re.compile(r'org\.slf4j', re.IGNORECASE),
    'jul':      re.compile(r'java\.util\.logging', re.IGNORECASE),
}
_HTTP_CLIENTS = {
    'apache-httpclient': re.compile(r'org\.apache\.http\.client', re.IGNORECASE),
    'okhttp':   re.compile(r'okhttp3', re.IGNORECASE),
    'resttemplate': re.compile(r'RestTemplate', re.IGNORECASE),
    'feign':    re.compile(r'feign\.', re.IGNORECASE),
    'urlconnection': re.compile(r'HttpURLConnection', re.IGNORECASE),
}


def _detect_libs(java_files: List[Path], patterns: Dict[str, re.Pattern]) -> Dict[str, List[str]]:
    """Return {lib_name: [files using it]}."""
    usage: Dict[str, List[str]] = {}
    for fp in java_files:
        content = _read(fp)
        if not content:
            continue
        rel = str(fp)
        for lib, pat in patterns.items():
            if pat.search(content):
                usage.setdefault(lib, []).append(rel)
    return usage


def check_p20(root: Path) -> PrincipleResult:
    _s = get_spec('P20')
    result = PrincipleResult(_s.id, _s.name, _s.priority)

    java_files = _collect(root, '.java')

    # Rule 1: multiple JSON libs
    json_usage = _detect_libs(java_files, _JSON_LIBS)
    result.checks_run += 1
    active_json = {k for k, v in json_usage.items() if v}
    if len(active_json) <= 1:
        result.checks_passed += 1
    else:
        result.add_finding(Finding('(全域)', 0,
                                   f'發現多個 JSON 函式庫並存：{", ".join(sorted(active_json))}',
                                   'HIGH', '技術多樣性過高 — JSON 庫'))

    # Rule 2: multiple logging frameworks
    log_usage = _detect_libs(java_files, _LOG_LIBS)
    result.checks_run += 1
    active_log = {k for k, v in log_usage.items() if v}
    if len(active_log) <= 1:
        result.checks_passed += 1
    else:
        result.add_finding(Finding('(全域)', 0,
                                   f'發現多個日誌框架並存：{", ".join(sorted(active_log))}',
                                   'MEDIUM', '技術多樣性過高 — 日誌框架'))

    # Rule 3: multiple HTTP clients
    http_usage = _detect_libs(java_files, _HTTP_CLIENTS)
    result.checks_run += 1
    active_http = {k for k, v in http_usage.items() if v}
    if len(active_http) <= 1:
        result.checks_passed += 1
    else:
        result.add_finding(Finding('(全域)', 0,
                                   f'發現多個 HTTP 用戶端並存：{", ".join(sorted(active_http))}',
                                   'LOW', '技術多樣性過高 — HTTP 用戶端'))

    return result


# ══════════════════════════════════════════════════════════════════════════════
# P21 – Interoperability
# 標準 API、訊息格式（JSON/XML）、協議
# ══════════════════════════════════════════════════════════════════════════════

_HARDCODED_IP = re.compile(
    r'(?:http[s]?://|//)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::\d+)?',
    re.IGNORECASE
)
_CONTENT_TYPE = re.compile(r'Content-Type', re.IGNORECASE)
_JSON_RESPONSE = re.compile(r'application/json', re.IGNORECASE)
_API_ANNOTATION = re.compile(r'@Api\s*\(', re.IGNORECASE)
_REST_METHODS = re.compile(r'@(?:GET|POST|PUT|DELETE|PATCH|RequestMapping|GetMapping|PostMapping)\b')
_STANDARD_FORMAT = re.compile(r'(?:JSONObject|JSONArray|ObjectMapper|Gson|XmlMapper)', re.IGNORECASE)


def check_p21(root: Path) -> PrincipleResult:
    _s = get_spec('P21')
    result = PrincipleResult(_s.id, _s.name, _s.priority)

    java_files = _collect(root, '.java')
    jsp_files  = _collect(root, '.jsp')

    has_api_doc    = False
    has_std_format = False

    # Java checks
    for fp in java_files:
        content = _read(fp)
        if not content:
            continue
        rel = str(fp.relative_to(root))
        lvs = _lines(content)

        if _API_ANNOTATION.search(content):
            has_api_doc = True
        if _STANDARD_FORMAT.search(content):
            has_std_format = True

        # Rule 1: hardcoded IP addresses
        for ln, line in lvs:
            result.checks_run += 1
            if _HARDCODED_IP.search(line) and not line.strip().startswith('//'):
                result.add_finding(Finding(rel, ln, line.strip()[:120], 'HIGH',
                                           '硬編碼 IP 位址（應使用設定檔或服務發現）'))
            else:
                result.checks_passed += 1

    # JSP checks
    for fp in jsp_files:
        content = _read(fp)
        if not content:
            continue
        rel = str(fp.relative_to(root))

        # Rule 2: JSP returning JSON without Content-Type header
        result.checks_run += 1
        has_json_output = 'JSONObject' in content or 'toJSONString' in content or 'application/json' in content
        has_ct = _CONTENT_TYPE.search(content)
        if has_json_output and not has_ct:
            result.add_finding(Finding(rel, 0,
                                       'JSP 輸出 JSON 但未設定 Content-Type: application/json',
                                       'MEDIUM', '缺少 Content-Type 標頭'))
        else:
            result.checks_passed += 1

    # Rule 3: no @Api documentation
    result.checks_run += 1
    if has_api_doc:
        result.checks_passed += 1
    else:
        result.add_finding(Finding('(全域)', 0,
                                   '未發現 @Api 文件標記（Swagger/OpenAPI）',
                                   'LOW', '缺少 API 文件'))

    # Rule 4: no standard serialization format
    result.checks_run += 1
    if has_std_format:
        result.checks_passed += 1
    else:
        result.add_finding(Finding('(全域)', 0,
                                   '未發現標準 JSON/XML 序列化工具使用',
                                   'LOW', '缺少標準訊息格式'))

    return result


# ══════════════════════════════════════════════════════════════════════════════
# P6 – Service Orientation
# 微服務/模組化設計、鬆耦合
# ══════════════════════════════════════════════════════════════════════════════

_LAYER_PATTERNS = {
    'model':   re.compile(r'class\s+\w*(?:Model|VO|DTO|Entity|Bean)\b'),
    'dao':     re.compile(r'(?:class|interface)\s+\w*(?:DAO|Dao|Repository|Mapper)\b'),
    'service': re.compile(r'(?:class|interface)\s+\w*(?:Service|ServiceImpl)\b'),
    'action':  re.compile(r'(?:class|interface)\s+\w*(?:Action|Controller|Resource)\b'),
}
_FAT_CLASS_METHOD = re.compile(
    r'(?:public|protected|private)\s+(?:static\s+)?[\w<>\[\]]+\s+\w+\s*\([^)]*\)\s*\{',
)


def check_p6(root: Path) -> PrincipleResult:
    _s = get_spec('P6')
    result = PrincipleResult(_s.id, _s.name, _s.priority)

    java_files = _collect(root, '.java')

    layers_present = {k: False for k in _LAYER_PATTERNS}
    fat_classes: List[Tuple[str, int]] = []  # (rel, method_count)

    for fp in java_files:
        content = _read(fp)
        if not content:
            continue
        rel = str(fp.relative_to(root))

        for layer, pat in _LAYER_PATTERNS.items():
            if pat.search(content):
                layers_present[layer] = True

        # Rule 1: fat class (too many methods)
        method_count = len(_FAT_CLASS_METHOD.findall(content))
        result.checks_run += 1
        if method_count > 25:
            fat_classes.append((rel, method_count))
            result.add_finding(Finding(rel, 0,
                                       f'方法數量過多：{method_count} 個（建議 ≤25）',
                                       'MEDIUM', '過胖類別 — 違反單一責任原則'))
        else:
            result.checks_passed += 1

    # Rule 2: check each layer exists
    for layer, present in layers_present.items():
        result.checks_run += 1
        if present:
            result.checks_passed += 1
        else:
            result.add_finding(Finding('(全域)', 0,
                                       f'未發現 {layer.upper()} 層類別',
                                       'MEDIUM', f'缺少 {layer} 分層'))

    return result


# ══════════════════════════════════════════════════════════════════════════════
# P5 – Common Use Applications
# 共用元件、禁止重複造輪子
# ══════════════════════════════════════════════════════════════════════════════

def check_p5(root: Path) -> PrincipleResult:
    _s = get_spec('P5')
    result = PrincipleResult(_s.id, _s.name, _s.priority)

    java_files = _collect(root, '.java')

    # Build class name → [files] map to detect duplicates across modules
    class_names: Dict[str, List[str]] = {}
    for fp in java_files:
        content = _read(fp)
        if not content:
            continue
        rel = str(fp.relative_to(root))
        m = re.search(r'(?:public\s+)?(?:class|interface|enum)\s+(\w+)', content)
        if m:
            name = m.group(1)
            class_names.setdefault(name, []).append(rel)

    # Rule 1: duplicate class names in different modules
    for name, files in class_names.items():
        # Only flag if they're in different module directories
        module_set = set()
        for f in files:
            parts = Path(f).parts
            module_set.add(parts[0] if parts else '?')
        result.checks_run += 1
        if len(files) > 1 and len(module_set) > 1:
            result.add_finding(Finding(files[0], 0,
                                       f'類別 "{name}" 在 {len(files)} 個模組中重複定義：'
                                       f'{", ".join(files[:3])}{"…" if len(files) > 3 else ""}',
                                       'MEDIUM', '跨模組重複類別（應共用元件）'))
        else:
            result.checks_passed += 1

    # Rule 2: check for utility/common package
    has_common = any(
        'common' in str(fp).lower() or 'util' in str(fp).lower() or 'shared' in str(fp).lower()
        for fp in java_files
    )
    result.checks_run += 1
    if has_common:
        result.checks_passed += 1
    else:
        result.add_finding(Finding('(全域)', 0,
                                   '未發現 common/util/shared 共用套件',
                                   'LOW', '缺少共用元件套件'))

    return result


# ══════════════════════════════════════════════════════════════════════════════
# P4 – Business Continuity
# 錯誤處理、重試機制、熔斷器
# ══════════════════════════════════════════════════════════════════════════════

_EMPTY_CATCH = re.compile(
    r'catch\s*\([^)]+\)\s*\{[\s]*\}',
    re.DOTALL
)
_BROAD_CATCH = re.compile(r'catch\s*\(\s*Exception\s+\w+\s*\)')
_LOG_IN_CATCH = re.compile(r'catch\s*\([^)]+\)\s*\{[^}]*(?:log\.|logger\.|Logger\.|System\.err)', re.DOTALL)
_NULL_CHECK = re.compile(r'(?:!= null|== null|Objects\.requireNonNull|Optional\.of)')
_RETRY_PATTERN = re.compile(r'(?:retry|Retry|RetryTemplate|@Retryable)', re.IGNORECASE)
_CIRCUIT_BREAKER = re.compile(r'(?:HystrixCommand|@HystrixCommand|Resilience4j|CircuitBreaker|@CircuitBreaker)', re.IGNORECASE)


def check_p4(root: Path) -> PrincipleResult:
    _s = get_spec('P4')
    result = PrincipleResult(_s.id, _s.name, _s.priority)

    java_files = _collect(root, '.java')

    has_retry = False
    has_circuit_breaker = False

    for fp in java_files:
        content = _read(fp)
        if not content:
            continue
        rel = str(fp.relative_to(root))
        lvs = _lines(content)

        if _RETRY_PATTERN.search(content):
            has_retry = True
        if _CIRCUIT_BREAKER.search(content):
            has_circuit_breaker = True

        # Rule 1: empty catch blocks
        for m in _EMPTY_CATCH.finditer(content):
            ln = content[:m.start()].count('\n') + 1
            result.checks_run += 1
            result.add_finding(Finding(rel, ln,
                                       content[m.start():m.end()][:80].replace('\n', ' '),
                                       'HIGH', '空 catch 塊（吞掉例外）'))

        # Rule 2: broad Exception catch without logging
        for ln, line in lvs:
            result.checks_run += 1
            if _BROAD_CATCH.search(line):
                # check next few lines for logging
                snippet = '\n'.join(l for _, l in lvs[ln-1:ln+5])
                if not re.search(r'(?:log\.|logger\.|Logger\.|e\.printStackTrace)', snippet):
                    result.add_finding(Finding(rel, ln, line.strip()[:120], 'MEDIUM',
                                               'catch(Exception) 未記錄日誌'))
                else:
                    result.checks_passed += 1
            else:
                result.checks_passed += 1

        # Rule 3: null checks (positive signal — we count files that have them)
        result.checks_run += 1
        if _NULL_CHECK.search(content):
            result.checks_passed += 1
        else:
            result.add_finding(Finding(rel, 0,
                                       '未發現任何 null 防禦檢查',
                                       'LOW', '缺少 null 防禦'))

    # Rule 4: retry mechanism
    result.checks_run += 1
    if has_retry:
        result.checks_passed += 1
    else:
        result.add_finding(Finding('(全域)', 0,
                                   '未發現重試機制 (@Retryable / RetryTemplate)',
                                   'LOW', '缺少重試機制'))

    # Rule 5: circuit breaker
    result.checks_run += 1
    if has_circuit_breaker:
        result.checks_passed += 1
    else:
        result.add_finding(Finding('(全域)', 0,
                                   '未發現熔斷器 (Hystrix / Resilience4j)',
                                   'LOW', '缺少熔斷器'))

    return result


# ══════════════════════════════════════════════════════════════════════════════
# P7 – Compliance with Law
# 個資脫敏、稽核日誌
# ══════════════════════════════════════════════════════════════════════════════

_PII_LOG = re.compile(
    r'(?:log|logger|Logger)\.\w+\s*\([^)]*(?:password|passwd|pwd|idno|身分證|手機|mobile|phone|email)[^)]*\)',
    re.IGNORECASE
)
_AUDIT_LOG = re.compile(
    r'(?:audit|稽核|AuditLog|auditLog|audit_log)\s*[.(]',
    re.IGNORECASE
)
_PII_FIELDS = re.compile(
    r'(?:idNumber|idNo|nationalId|身分證|mobilePhone|cellPhone|emailAddress)\s*[=;,)]',
    re.IGNORECASE
)
_MASK_PATTERN = re.compile(
    r'(?:mask|脫敏|anonymize|obfuscat|replaceAll.*\*)',
    re.IGNORECASE
)
_PERSONAL_DATA_LOG = re.compile(
    r'(?:log|logger|Logger)\.\w+\s*\([^)]{0,200}(?:name|姓名|address|地址|birth|生日)[^)]*\)',
    re.IGNORECASE
)


def check_p7(root: Path) -> PrincipleResult:
    _s = get_spec('P7')
    result = PrincipleResult(_s.id, _s.name, _s.priority)

    java_files = _collect(root, '.java')
    has_audit  = False
    has_mask   = False
    pii_files  = []

    for fp in java_files:
        content = _read(fp)
        if not content:
            continue
        rel = str(fp.relative_to(root))
        lvs = _lines(content)

        if _AUDIT_LOG.search(content):
            has_audit = True
        if _MASK_PATTERN.search(content):
            has_mask = True
        if _PII_FIELDS.search(content):
            pii_files.append(rel)

        # Rule 1: PII fields being logged (password)
        for ln, line in lvs:
            result.checks_run += 1
            if _PII_LOG.search(line):
                result.add_finding(Finding(rel, ln, line.strip()[:120], 'HIGH',
                                           '個資/密碼欄位被寫入日誌'))
            else:
                result.checks_passed += 1

        # Rule 2: personal data in logs
        for ln, line in lvs:
            result.checks_run += 1
            if _PERSONAL_DATA_LOG.search(line):
                result.add_finding(Finding(rel, ln, line.strip()[:120], 'MEDIUM',
                                           '個人資料（姓名/地址）可能被寫入日誌'))
            else:
                result.checks_passed += 1

    # Rule 3: PII files exist but no masking found
    result.checks_run += 1
    if pii_files and not has_mask:
        result.add_finding(Finding('(全域)', 0,
                                   f'發現 {len(pii_files)} 個含個資欄位的檔案但未發現脫敏處理',
                                   'HIGH', '缺少個資脫敏'))
    else:
        result.checks_passed += 1

    # Rule 4: audit log
    result.checks_run += 1
    if has_audit:
        result.checks_passed += 1
    else:
        result.add_finding(Finding('(全域)', 0,
                                   '未發現稽核日誌寫入（AuditLog）',
                                   'MEDIUM', '缺少稽核日誌'))

    return result


# ══════════════════════════════════════════════════════════════════════════════
# Main runner
# ══════════════════════════════════════════════════════════════════════════════

CHECKERS = [
    check_p15,
    check_p16,
    check_p20,
    check_p21,
    check_p6,
    check_p5,
    check_p4,
    check_p7,
]


def run_all_checks(project_root: str) -> ProjectCheckResult:
    from datetime import datetime
    root = Path(project_root)
    total = len(_collect(root, '.java')) + len(_collect(root, '.jsp')) + len(_collect(root, '.properties'))

    project_result = ProjectCheckResult(
        root=project_root,
        total_files_scanned=total,
        generated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    )

    for checker in CHECKERS:
        pr = checker(root)
        project_result.results.append(pr)

    return project_result


# ── Quick CLI test ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    pr = run_all_checks(root)
    print(f"Scanned {pr.total_files_scanned} files in {pr.root}")
    for r in pr.results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] {r.principle_id} {r.principle_name}: score={r.score}%  findings={len(r.findings)}")
        for f in r.findings[:3]:
            print(f"         {f.severity} line {f.line_no}: {f.rule}")
            print(f"           {f.evidence[:80]}")
