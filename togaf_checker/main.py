"""
main.py
-------
Entry point for the TOGAF Principle Checker.

Usage:
    python main.py                        # scan once, use defaults
    python main.py --once                 # same
    python main.py --daemon               # stay alive, run daily at 10:00
    python main.py --root D:/myproject    # override project root
    python main.py --time 09:30 --daemon  # daemon at 09:30

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

DEFAULT_PROJECT_ROOT = os.environ.get(
    "TOGAF_PROJECT_ROOT",
    str(Path(__file__).parent.parent)   # one level above togaf_checker/
)

DEFAULT_OUTPUT_DIR = os.environ.get(
    "TOGAF_OUTPUT_DIR",
    str(Path(__file__).parent.parent / "docs" / "generated")
)

FILENAME_TEMPLATE = os.environ.get(
    "TOGAF_FILENAME",
    "台水TOGAF合規報告_{datetime}.docx"
)

SCHEDULE_TIME = os.environ.get("TOGAF_TIME", "10:00")

KEEP_LAST_N = int(os.environ.get("TOGAF_KEEP_LAST", "30"))

# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("togaf_checker")


def _add_file_log(output_dir: str):
    log_path = Path(output_dir) / "togaf_checker.log"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logging.getLogger().addHandler(fh)


# ── Core logic ─────────────────────────────────────────────────────────────────

def generate(project_root: str, output_dir: str) -> str:
    """
    Run TOGAF checks on *project_root* and write a Word report to *output_dir*.
    Returns the full path of the generated file.
    """
    from checker import run_all_checks
    from report_builder import build_report

    # 1. Static analysis
    log.info(f"Scanning project: {project_root}")
    result = run_all_checks(project_root)

    passed  = sum(1 for r in result.results if r.passed)
    total_p = len(result.results)
    high_cnt = sum(
        sum(1 for f in r.findings if f.severity == 'HIGH')
        for r in result.results
    )
    log.info(
        f"Analysis complete: {result.total_files_scanned} files scanned, "
        f"{passed}/{total_p} principles passed, "
        f"{high_cnt} HIGH-severity findings."
    )

    # 2. Prepare output path
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    filename = FILENAME_TEMPLATE.replace("{datetime}", date_str)
    out_path = Path(output_dir) / filename
    tmp_path = out_path.with_suffix(".tmp.docx")

    # 3. Build Word report
    log.info(f"Building Word report -> {out_path}")
    build_report(result, str(tmp_path))

    # Atomic replace (handles file locked by Word)
    if out_path.exists():
        try:
            out_path.unlink()
        except PermissionError:
            ts  = datetime.now().strftime("%H%M%S")
            alt = out_path.with_stem(out_path.stem + f"_{ts}")
            log.warning(f"Target file locked. Saving as: {alt.name}")
            out_path = alt
    tmp_path.rename(out_path)

    size_kb = out_path.stat().st_size // 1024
    log.info(f"Report saved: {out_path}  ({size_kb} KB)")

    # 4. Rotate old files
    _rotate_old(output_dir, filename)

    return str(out_path)


def _rotate_old(output_dir: str, current_filename: str):
    if KEEP_LAST_N <= 0:
        return
    pattern = FILENAME_TEMPLATE.replace("{datetime}", "????????_????")
    existing = sorted(
        Path(output_dir).glob(pattern),
        key=lambda p: p.stat().st_mtime
    )
    while len(existing) > KEEP_LAST_N:
        victim = existing.pop(0)
        if victim.name != current_filename:
            log.info(f"Rotating old report: {victim.name}")
            victim.unlink(missing_ok=True)


# ── Daemon mode ────────────────────────────────────────────────────────────────

def _parse_hhmm(s: str):
    h, m = s.split(":")
    return int(h), int(m)


def _seconds_until(h: int, m: int) -> float:
    from datetime import timedelta
    now    = datetime.now()
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def run_daemon(project_root: str, output_dir: str):
    target_h, target_m = _parse_hhmm(SCHEDULE_TIME)
    log.info(
        f"Daemon started. Will run daily at {SCHEDULE_TIME} "
        f"(project: {project_root})"
    )
    while True:
        wait     = _seconds_until(target_h, target_m)
        next_run = datetime.now().strftime("%Y-%m-%d") + f" {SCHEDULE_TIME}:00"
        log.info(f"Next run at {next_run} (in {wait/3600:.1f} h). Sleeping...")
        time.sleep(wait)
        try:
            generate(project_root, output_dir)
        except Exception as e:
            log.exception(f"Generation failed: {e}")
        time.sleep(70)   # avoid re-triggering in same minute


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    global SCHEDULE_TIME   # must be first line in function

    parser = argparse.ArgumentParser(
        description="TOGAF Principle Checker — scan source code and generate compliance report."
    )
    parser.add_argument("--root",   default=DEFAULT_PROJECT_ROOT,
                        help="Project root directory to scan.")
    parser.add_argument("--out",    default=DEFAULT_OUTPUT_DIR,
                        help="Output directory for .docx report.")
    parser.add_argument("--time",   default=SCHEDULE_TIME,
                        help="Daily run time in daemon mode, e.g. 10:00.")
    parser.add_argument("--daemon", action="store_true",
                        help="Stay alive and run daily at --time.")
    parser.add_argument("--once",   action="store_true",
                        help="Run once and exit (default).")
    args = parser.parse_args()

    SCHEDULE_TIME = args.time

    # Make helper modules importable from the same folder
    sys.path.insert(0, str(Path(__file__).parent))

    _add_file_log(args.out)

    if args.daemon:
        run_daemon(args.root, args.out)
    else:
        try:
            out = generate(args.root, args.out)
            print(f"\n[OK] Report ready: {out}")
        except Exception as e:
            log.exception(f"Generation failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
