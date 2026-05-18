"""
analyzer.py
-----------
Scans Java / JSP / Properties source files and extracts architecture metadata.
"""

import re
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional


# ── Data Models ───────────────────────────────────────────────────────────────

@dataclass
class JavaClass:
    filepath: str
    package: str
    name: str
    kind: str          # class | interface | enum
    parent: str        # extends / implements
    unit_id: str
    cache_region: str
    methods: List[str] = field(default_factory=list)
    api_paths: List[str] = field(default_factory=list)
    db_tables: List[str] = field(default_factory=list)
    timer_schedule: str = ""
    annotations: List[str] = field(default_factory=list)
    layer: str = ""    # model | dao | service | api | action | timer | home | other


@dataclass
class JspEndpoint:
    filepath: str
    name: str
    http_method: str
    cors: bool
    request_fields: List[str] = field(default_factory=list)
    response_fields: List[str] = field(default_factory=list)
    flow_steps: List[str] = field(default_factory=list)


@dataclass
class PropertyFile:
    filepath: str
    entries: Dict[str, str] = field(default_factory=dict)


@dataclass
class Module:
    name: str               # e.g. ecpsso / waterHrSync / waterCusSSO
    unit_id: str
    classes: List[JavaClass] = field(default_factory=list)
    jsps: List[JspEndpoint] = field(default_factory=list)
    properties: List[PropertyFile] = field(default_factory=list)
    description: str = ""


@dataclass
class ProjectInfo:
    root: str
    name: str
    modules: List[Module] = field(default_factory=list)
    generated_at: str = ""
    db_tables: List[str] = field(default_factory=list)


# ── Helpers ───────────────────────────────────────────────────────────────────

# Directories to skip entirely (matched against each path component below root)
SKIP_DIRS = {
    '.git', '.claude', 'target', 'build', '__pycache__',
    'node_modules', '.tmp_ccms', 'update', 'archive',
    # "ciopy" dirs are copy/backup clones – folder name pattern below
}

# Folder name substrings that mark a module as a backup/copy (case-insensitive)
COPY_FOLDER_MARKERS = ('ciopy', ' - copy', '-copy', '_copy', '複製', 'backup', 'bak')

# JSP filename substrings that mark a file as a backup/copy
COPY_FILE_MARKERS   = ('複製', ' - copy', '-copy', '_copy', 'backup')


def _skip(path: Path, root: Path | None = None) -> bool:
    """Return True if *path* should be excluded from scanning.

    Checks only path parts BELOW *root* so that parent directory names
    (e.g. '.claude' in the worktree path) do not accidentally match.
    """
    if root and path.is_relative_to(root):
        parts = path.relative_to(root).parts
    else:
        parts = path.parts

    for part in parts:
        # standard skip-dirs
        if part in SKIP_DIRS:
            return True
        # folders whose name contains a copy/backup marker
        pl = part.lower()
        if any(marker in pl for marker in COPY_FOLDER_MARKERS):
            return True

    return False


def _skip_jsp(path: Path) -> bool:
    """Return True for JSP backup/copy/archive files."""
    name = path.stem  # filename without extension
    return any(marker in name for marker in COPY_FILE_MARKERS)


def _read(filepath: Path) -> str:
    for enc in ('utf-8', 'cp950', 'big5', 'latin-1'):
        try:
            return filepath.read_text(encoding=enc)
        except (UnicodeDecodeError, Exception):
            continue
    return ""


def _detect_layer(name: str, package: str) -> str:
    n = name.lower()
    p = package.lower()
    if 'home' in n:      return 'home'
    if 'timer' in n or 'routine' in n or 'rountine' in n: return 'timer'
    if 'daoimpl' in n:   return 'dao'
    if 'dao' in n:       return 'dao'
    if 'serviceimpl' in n: return 'service'
    if 'service' in n:   return 'service'
    if 'apiimpl' in n:   return 'api'
    if 'api' in n:       return 'api'
    if 'actionimpl' in n: return 'action'
    if 'action' in n:    return 'action'
    if 'model' in n:     return 'model'
    return 'other'


# ── Java Parser ───────────────────────────────────────────────────────────────

class JavaParser:
    # tables referenced in SQL strings or entity names
    TABLE_PATTERN = re.compile(
        r'(?:FROM|JOIN|INTO|UPDATE)\s+([A-Za-z_][A-Za-z0-9_]+)',
        re.IGNORECASE
    )
    METHOD_PATTERN = re.compile(
        r'(?:public|protected|private)\s+'
        r'(?:static\s+|final\s+|synchronized\s+)*'
        r'(?:<[^>]+>\s+)?'
        r'[\w<>\[\]]+\s+'
        r'(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{'
    )
    API_PATH_PATTERN = re.compile(r'@Api\s*\([^)]*path\s*=\s*"([^"]+)"', re.DOTALL)
    UNIT_ID_PATTERN  = re.compile(r'UNIT_ID\s*=\s*"([^"]+)"')
    CACHE_REGION_PATTERN = re.compile(r'[Cc]ache[Rr]egion\s*=?\s*"([^"]+)"')
    TIMER_PATTERN    = re.compile(r'(?:cron|schedule|CRON)\s*[=:]\s*"([^"]+)"', re.IGNORECASE)
    ANNOTATION_PATTERN = re.compile(r'@(\w+)(?:\([^)]*\))?')

    SKIP_METHODS = {
        'if', 'for', 'while', 'switch', 'catch', 'try',
        'class', 'interface', 'new', 'return'
    }

    def parse(self, filepath: Path) -> Optional[JavaClass]:
        content = _read(filepath)
        if not content:
            return None

        # package
        pkg_m = re.search(r'package\s+([\w.]+)\s*;', content)
        package = pkg_m.group(1) if pkg_m else ''

        # class / interface / enum
        cls_m = re.search(
            r'(?:public\s+)?(?:abstract\s+)?'
            r'(class|interface|enum)\s+(\w+)'
            r'(?:\s+extends\s+([\w<>, ]+))?'
            r'(?:\s+implements\s+([\w<>, ]+))?',
            content
        )
        if not cls_m:
            return None

        kind   = cls_m.group(1)
        name   = cls_m.group(2)
        parent = (cls_m.group(3) or cls_m.group(4) or '').strip()

        # annotations (top-level)
        annotations = list(set(self.ANNOTATION_PATTERN.findall(content[:500])))

        # methods
        raw_methods = self.METHOD_PATTERN.findall(content)
        methods = [m for m in raw_methods if m not in self.SKIP_METHODS]

        # @Api paths
        api_paths = self.API_PATH_PATTERN.findall(content)

        # DB tables from SQL strings
        sql_strings = re.findall(r'"([^"]{20,})"', content)
        tables = set()
        for s in sql_strings:
            tables.update(self.TABLE_PATTERN.findall(s))
        # filter obvious non-table tokens
        ignore = {'SELECT','FROM','WHERE','AND','OR','AS','ON','SET','NULL','TRUE','FALSE','JOIN'}
        tables = [t for t in tables if t.upper() not in ignore and not t[0].isdigit()]

        unit_id_m  = self.UNIT_ID_PATTERN.search(content)
        cache_m    = self.CACHE_REGION_PATTERN.search(content)
        timer_m    = self.TIMER_PATTERN.search(content)

        layer = _detect_layer(name, package)

        return JavaClass(
            filepath=str(filepath),
            package=package,
            name=name,
            kind=kind,
            parent=parent,
            unit_id=unit_id_m.group(1) if unit_id_m else '',
            cache_region=cache_m.group(1) if cache_m else '',
            methods=methods[:30],        # cap
            api_paths=api_paths,
            db_tables=tables,
            timer_schedule=timer_m.group(1) if timer_m else '',
            annotations=annotations,
            layer=layer,
        )


# ── JSP Parser ────────────────────────────────────────────────────────────────

class JspParser:
    def parse(self, filepath: Path) -> Optional[JspEndpoint]:
        content = _read(filepath)
        if not content:
            return None

        name = filepath.stem

        # HTTP method hint
        http_method = 'POST' if 'POST' in content.upper() or 'request.getParameter' in content else 'GET'

        # CORS
        cors = 'Access-Control-Allow-Origin' in content or 'cors' in content.lower()

        # JSON field names in request
        req_fields = list(set(re.findall(r'\.getString\("(\w+)"\)', content)))
        req_fields += list(set(re.findall(r'"(\w+)"\s*:', content)))
        req_fields = list(set(req_fields))[:10]

        # flow: service calls
        flow = re.findall(r'(?:getService|Home)\(\)\s*\.\s*(\w+)\s*\(', content)
        flow_steps = [f"呼叫 {s}()" for s in set(flow)]

        return JspEndpoint(
            filepath=str(filepath),
            name=name,
            http_method=http_method,
            cors=cors,
            request_fields=req_fields,
            flow_steps=flow_steps,
        )


# ── Properties Parser ─────────────────────────────────────────────────────────

class PropertiesParser:
    def parse(self, filepath: Path) -> PropertyFile:
        content = _read(filepath)
        entries = {}
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, _, v = line.partition('=')
                entries[k.strip()] = v.strip()
        return PropertyFile(filepath=str(filepath), entries=entries)


# ── Module Detector ───────────────────────────────────────────────────────────

MODULE_DIRS = {
    'ecpsso':            'SSO 登入紀錄核心模組（ECP Plugin JAR）',
    'waterCusSSO':       '前端登入入口（WAR，含 JSP 登入頁面）',
    'waterHrSync':       'HR 同步與聊天摘要模組（ECP Plugin JAR）',
    'waterImportTimer':  '排程匯入服務（Timer Plugin JAR）',
}


def _detect_module(filepath: Path, root: Path) -> str:
    rel = filepath.relative_to(root)
    for part in rel.parts:
        if part in MODULE_DIRS:
            return part
        for key in MODULE_DIRS:
            if key.lower() in part.lower():
                return key
    return 'other'


# ── Main Analyzer ─────────────────────────────────────────────────────────────

class ProjectAnalyzer:
    def __init__(self, project_root: str):
        self.root = Path(project_root)
        self._java_parser = JavaParser()
        self._jsp_parser  = JspParser()
        self._prop_parser = PropertiesParser()

    def analyze(self) -> ProjectInfo:
        from datetime import datetime

        info = ProjectInfo(
            root=str(self.root),
            name='台灣自來水公司 資訊整合系統',
            generated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        )

        modules: Dict[str, Module] = {}

        def get_module(name: str) -> Module:
            if name not in modules:
                modules[name] = Module(
                    name=name,
                    unit_id='',
                    description=MODULE_DIRS.get(name, name),
                )
            return modules[name]

        all_tables: set = set()

        root = self.root

        # ── Java files
        for fp in sorted(root.rglob('*.java')):
            if _skip(fp, root):
                continue
            jc = self._java_parser.parse(fp)
            if not jc:
                continue
            mod_name = _detect_module(fp, root)
            mod = get_module(mod_name)
            mod.classes.append(jc)
            if jc.unit_id and not mod.unit_id:
                mod.unit_id = jc.unit_id
            all_tables.update(jc.db_tables)

        # ── JSP files (skip backup/archive copies)
        for fp in sorted(root.rglob('*.jsp')):
            if _skip(fp, root) or _skip_jsp(fp):
                continue
            je = self._jsp_parser.parse(fp)
            if not je:
                continue
            mod_name = _detect_module(fp, root)
            mod = get_module(mod_name)
            mod.jsps.append(je)

        # ── Properties files
        for fp in sorted(root.rglob('*.properties')):
            if _skip(fp, root):
                continue
            pf = self._prop_parser.parse(fp)
            mod_name = _detect_module(fp, root)
            mod = get_module(mod_name)
            mod.properties.append(pf)

        # preserve a consistent order
        for key in list(MODULE_DIRS.keys()) + ['other']:
            if key in modules:
                info.modules.append(modules[key])

        info.db_tables = sorted(all_tables)
        return info


# ── Quick CLI test ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys, json
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    info = ProjectAnalyzer(root).analyze()
    print(f"Modules: {[m.name for m in info.modules]}")
    for m in info.modules:
        print(f"  [{m.name}] unit_id={m.unit_id}  classes={len(m.classes)}  jsps={len(m.jsps)}")
    print(f"DB tables found: {info.db_tables}")
