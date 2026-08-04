"""Offline proof that the LinkedIn write functions fail closed.

No network. Nothing is posted. Each call must RAISE before it ever reaches
LinkedIn, because Greg's same-day per-comment approval is the only key.

Run:  python test_approval_gate_offline.py

This is layer 2 of the fix for the 2026-07-31 unauthorized comments. Layer 1 is
the Claude hook (.claude/hooks/block_linkedin_autopost.py, 17-case suite). This
layer protects the module when it runs OUTSIDE Claude: Task Scheduler, a stray
python call, or any future script that imports it.
"""
import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import linkedin_client as lc  # noqa: E402

APPROVAL = lc.APPROVAL_FILE
BACKUP = APPROVAL + ".gatetestbak"
results = []


def expect_raise(name, fn):
    try:
        fn()
    except RuntimeError as e:
        ok = "REFUSED" in str(e)
        results.append((ok, name))
        print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else "  wrong error: %s" % e))
        return
    except Exception as e:
        results.append((False, name))
        print("FAIL  %s  raised %s instead of the approval refusal" % (name, type(e).__name__))
        return
    results.append((False, name))
    print("FAIL  " + name + "  DID NOT RAISE (a write path is open)")


def write_approval(numbers, day_offset=0, cls="comment", source="comments-2026-08-04.md"):
    with open(APPROVAL, "w", encoding="utf-8") as f:
        json.dump({"date": (date.today() + timedelta(days=day_offset)).isoformat(),
                   "approved": [{"n": n, "source": source} for n in numbers],
                   "class": cls, "greg_wording": "TEST", "granted_at": "test"}, f)


def _write_bare(numbers):
    """The old, broken shape: bare ints with no source binding."""
    with open(APPROVAL, "w", encoding="utf-8") as f:
        json.dump({"date": date.today().isoformat(), "approved": numbers,
                   "class": "comment", "greg_wording": "TEST"}, f)


def main():
    had = os.path.exists(APPROVAL)
    if had:
        os.replace(APPROVAL, BACKUP)
    try:
        expect_raise("post_comment with no approval on file",
                     lambda: lc.post_comment("urn:li:activity:123", "text", 1))
        expect_raise("post_to_linkedin with no approval on file",
                     lambda: lc.post_to_linkedin("some post body"))
        expect_raise("setup_oauth (token minting) with no approval",
                     lambda: lc.setup_oauth())

        write_approval([2, 3])
        expect_raise("post_comment for a number Greg did NOT approve",
                     lambda: lc.post_comment("urn:li:activity:123", "text", 8))

        write_approval([1], day_offset=-1)
        expect_raise("post_comment on yesterday's approval",
                     lambda: lc.post_comment("urn:li:activity:123", "text", 1))

        os.remove(APPROVAL)
        with open(APPROVAL, "w", encoding="utf-8") as f:
            f.write("{ not valid json")
        expect_raise("post_comment with a malformed approval file",
                     lambda: lc.post_comment("urn:li:activity:123", "text", 1))

        # Hardened 2026-08-04 after the council review: a comment GO must never
        # authorize an original post or a fresh 60-day token, and omitting the
        # comment number must not downgrade per-comment approval to per-day.
        write_approval([1, 2, 3])
        expect_raise("comment approval does NOT unlock post_to_linkedin",
                     lambda: lc.post_to_linkedin("an original post to Greg's feed"))
        expect_raise("comment approval does NOT unlock token minting",
                     lambda: lc.setup_oauth())
        expect_raise("post_comment refuses when comment_number is omitted",
                     lambda: lc.post_comment("urn:li:activity:123", "text"))
        expect_raise("bare-integer approvals are rejected outright",
                     lambda: (_write_bare([1, 2, 3]),
                              lc.post_comment("urn:li:activity:123", "text", 1))[1])
    finally:
        if os.path.exists(APPROVAL):
            os.remove(APPROVAL)
        if had:
            os.replace(BACKUP, APPROVAL)

    failed = [r for r in results if not r[0]]
    print("\nRESULT: %d/%d passed" % (len(results) - len(failed), len(results)))
    if failed:
        return 1
    print("Every write function fails closed without Greg's same-day approval.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
