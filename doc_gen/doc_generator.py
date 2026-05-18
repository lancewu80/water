"""
doc_generator.py
----------------
Main entry point.

Usage:
    python doc_generator.py                        # generate once, use config defaults
    python doc_generator.py --once                 # same
    python doc_generator.py --daemon               # stay alive, run daily at 10:00
    python doc_generator.py --root D:/myproject    # override project root

Schedule (Windows Task Scheduler):
    Use setup_scheduler.bat or setup_scheduler.ps1 to register a daily task.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────

# Project root to analyse (can be overridden via --root or environment variable)
DEFAULT_PROJECT_ROOT = os.environ.get(
    "DOC_GEN_PROJECT_ROOT",
    str(Path(__file__).parent.parent)           # one level above doc_gen/
)

# Folder where generated .docx files are saved
DEFAULT_OUTPUT_DIR = os.environ.get(
    "DOC_GEN_OUTPUT_DIR",
    str(Path(__file__).parent.parent / "docs" / "generated")
)

# Filename template  –  {date} is replaced with YYYYMMDD
FILENAME_TEMPLATE = os.environ.get(
    "DOC_GEN_FILENAME",
    "台水資訊整合系統_設計文件_{date}.docx"
)

# Daemon mode: time-of-day to run (24-hour HH:MM)
SCHEDULE_TIME = os.environ.get("DOC_GEN_TIME", "10:00")

# How many old docs to keep (0 = keep all)
KEEP_LAST_N = int(os.environ.get("DOC_GEN_KEEP_LAST", "30"))

# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("doc_gen")


# ── Core logic ─────────────────────────────────────────────────────────────────

def _add_file_log(output_dir: str):
    """Also write logs to a file in output_dir."""
    log_path = Path(output_dir) / "doc_gen.log"
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logging.getLogger().addHandler(fh)


def generate(project_root: str, output_dir: str) -> str:
    """
    Analyse *project_root* and write a Word document to *output_dir*.
    Returns the full path of the generated file.
    """
    from analyzer import ProjectAnalyzer
    from word_builder import build_document

    # 1. Analyse source code
    log.info(f"Analysing project: {project_root}")
    info = ProjectAnalyzer(project_root).analyze()
    log.info(
        f"Found {len(info.modules)} modules, "
        f"{sum(len(m.classes) for m in info.modules)} classes, "
        f"{sum(len(m.jsps) for m in info.modules)} JSP files."
    )

    # 2. Prepare output path
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    date_str  = datetime.now().strftime("%Y%m%d")
    filename  = FILENAME_TEMPLATE.replace("{date}", date_str)
    out_path  = Path(output_dir) / filename
    # Write to a temp file first, then rename — avoids PermissionError
    # if the target is currently open in Word.
    tmp_path  = out_path.with_suffix(".tmp.docx")

    # 3. Build Word document
    log.info(f"Building Word document → {out_path}")
    build_document(info, str(tmp_path))

    # Atomic replace: remove old file if present, then rename temp
    if out_path.exists():
        try:
            out_path.unlink()
        except PermissionError:
            ts = datetime.now().strftime("%H%M%S")
            alt = out_path.with_stem(out_path.stem + f"_{ts}")
            log.warning(f"Target file locked by another process. Saving as: {alt.name}")
            out_path = alt
    tmp_path.rename(out_path)

    size_kb = out_path.stat().st_size // 1024
    log.info(f"Document saved: {out_path}  ({size_kb} KB)")
    out_path = str(out_path)

    # 4. Rotate old files
    _rotate_old_docs(output_dir, filename)

    return out_path


def _rotate_old_docs(output_dir: str, current_filename: str):
    """Delete oldest generated docs if KEEP_LAST_N > 0."""
    if KEEP_LAST_N <= 0:
        return
    pattern = FILENAME_TEMPLATE.replace("{date}", "*")
    existing = sorted(Path(output_dir).glob(
        pattern.replace("*", "????????")  # 8-digit date
    ), key=lambda p: p.stat().st_mtime)
    # remove from oldest
    while len(existing) > KEEP_LAST_N:
        victim = existing.pop(0)
        if victim.name != current_filename:
            log.info(f"Rotating old doc: {victim.name}")
            victim.unlink(missing_ok=True)


# ── Daemon mode ────────────────────────────────────────────────────────────────

def _parse_hhmm(s: str):
    h, m = s.split(":")
    return int(h), int(m)


def _seconds_until(target_h: int, target_m: int) -> float:
    now = datetime.now()
    target = now.replace(hour=target_h, minute=target_m, second=0, microsecond=0)
    if target <= now:
        # next occurrence tomorrow
        from datetime import timedelta
        target += timedelta(days=1)
    return (target - now).total_seconds()


def run_daemon(project_root: str, output_dir: str):
    """Block forever, running generate() once per day at SCHEDULE_TIME."""
    target_h, target_m = _parse_hhmm(SCHEDULE_TIME)
    log.info(
        f"Daemon started. Will generate documents daily at "
        f"{SCHEDULE_TIME} (project: {project_root})"
    )
    while True:
        wait = _seconds_until(target_h, target_m)
        next_run = datetime.now().strftime("%Y-%m-%d") + f" {SCHEDULE_TIME}:00"
        log.info(f"Next run at {next_run} (in {wait/3600:.1f} hours). Sleeping…")
        time.sleep(wait)
        try:
            generate(project_root, output_dir)
        except Exception as e:
            log.exception(f"Generation failed: {e}")
        # sleep 70 s to avoid re-triggering in the same minute
        time.sleep(70)


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    global SCHEDULE_TIME  # declare at top of function, before any use

    parser = argparse.ArgumentParser(
        description="Auto-generate Architecture & Design Document in Word format."
    )
    parser.add_argument("--root",   default=DEFAULT_PROJECT_ROOT,
                        help="Project root directory to analyse.")
    parser.add_argument("--out",    default=DEFAULT_OUTPUT_DIR,
                        help="Output directory for .docx files.")
    parser.add_argument("--time",   default=SCHEDULE_TIME,
                        help="Daily run time in daemon mode, e.g. 10:00.")
    parser.add_argument("--daemon", action="store_true",
                        help="Stay alive and run daily at --time.")
    parser.add_argument("--once",   action="store_true",
                        help="Run once and exit (default behaviour).")
    args = parser.parse_args()

    # Apply CLI override
    SCHEDULE_TIME = args.time

    # Ensure helper modules are importable (they live in the same folder)
    sys.path.insert(0, str(Path(__file__).parent))

    _add_file_log(args.out)

    if args.daemon:
        run_daemon(args.root, args.out)
    else:
        # --once or no flag → run once
        try:
            out = generate(args.root, args.out)
            print(f"\n[OK] Document ready: {out}")
        except Exception as e:
            log.exception(f"Generation failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
