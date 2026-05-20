"""Final DB cleanup: make `channels` table contain ONLY clean eligibles.

After this script:
  - `channels` table → only rows where is_target=1 AND subscribers>=1000
                        AND country in (Brasil,Brazil) OR (lang_recovered passing strict pt)
  - `rejected_channel_ids` → just channel_id PKs of channels we've confirmed
                              are not eligible (subs<1000 or non-Brazil).
                              Used by production scraper for dedup.
  - error rows: deleted (transient, can retry next discovery pass)
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / "results.db"


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    print("=== BEFORE ===")
    for label, sql in [
        ("total in channels", "SELECT COUNT(*) FROM channels"),
        ("eligible (target+>=1k)", "SELECT COUNT(*) FROM channels WHERE is_target=1 AND subscribers>=1000"),
        ("dirty: errors", "SELECT COUNT(*) FROM channels WHERE error IS NOT NULL"),
        ("dirty: short_circuit (subs<1k)", "SELECT COUNT(*) FROM channels WHERE short_circuit=1"),
        ("dirty: is_target=0 (non-BR)", "SELECT COUNT(*) FROM channels WHERE is_target=0 AND error IS NULL AND short_circuit=0"),
    ]:
        n = cur.execute(sql).fetchone()[0]
        print(f"  {label:40s} = {n:>6d}")

    print("\n=== MIGRATING ===")
    # Create rejected table
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS rejected_channel_ids (
            channel_id TEXT PRIMARY KEY,
            reason TEXT
        );
    """)

    # Move short_circuit (subs<1k) to rejected
    n_short = cur.execute(
        """INSERT OR IGNORE INTO rejected_channel_ids (channel_id, reason)
           SELECT channel_id, 'subs<1000' FROM channels WHERE short_circuit=1"""
    ).rowcount
    print(f"  → moved {n_short} 'subs<1000' rows to rejected_channel_ids")

    # Move definitive non-BR (is_target=0 and no error) to rejected
    n_nonbr = cur.execute(
        """INSERT OR IGNORE INTO rejected_channel_ids (channel_id, reason)
           SELECT channel_id, COALESCE('country='||country, 'is_target=0')
             FROM channels
            WHERE is_target=0 AND error IS NULL AND short_circuit=0"""
    ).rowcount
    print(f"  → moved {n_nonbr} 'non-BR confirmed' rows to rejected_channel_ids")

    # Delete error rows (transient, can retry)
    n_err = cur.execute(
        "DELETE FROM channels WHERE error IS NOT NULL"
    ).rowcount
    print(f"  → deleted {n_err} 'error' rows (transient, can retry next time)")

    # Delete short_circuit and non-BR rows from channels (already in rejected)
    n_del_short = cur.execute(
        "DELETE FROM channels WHERE short_circuit=1"
    ).rowcount
    n_del_nonbr = cur.execute(
        "DELETE FROM channels WHERE is_target=0"
    ).rowcount
    print(f"  → cleaned {n_del_short + n_del_nonbr} non-eligible rows from channels")

    conn.commit()

    print("\n=== AFTER ===")
    for label, sql in [
        ("clean channels (all eligible)", "SELECT COUNT(*) FROM channels"),
        ("  → country=Brasil/Brazil", "SELECT COUNT(*) FROM channels WHERE country IN ('Brasil','Brazil')"),
        ("  → lang_recovered (strict pt)", "SELECT COUNT(*) FROM channels WHERE target_reason='country=None,lang=pt'"),
        ("  → all is_target=1 + subs>=1k", "SELECT COUNT(*) FROM channels WHERE is_target=1 AND subscribers>=1000"),
        ("rejected_channel_ids (dedup table)", "SELECT COUNT(*) FROM rejected_channel_ids"),
    ]:
        n = cur.execute(sql).fetchone()[0]
        print(f"  {label:40s} = {n:>6d}")

    print("\n=== sanity check: any non-eligible left in channels? ===")
    leftover = cur.execute(
        "SELECT COUNT(*) FROM channels WHERE NOT (is_target=1 AND subscribers>=1000)"
    ).fetchone()[0]
    print(f"  non-eligible rows in channels: {leftover}  (should be 0)")

    conn.execute("VACUUM")  # reclaim disk space
    conn.close()
    print("\n✓ done — channels table is now 100% clean eligible only.")


if __name__ == "__main__":
    main()
