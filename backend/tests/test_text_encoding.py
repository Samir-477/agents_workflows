from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_report_sources_do_not_contain_utf8_mojibake_or_a_bom():
    for relative in (
        "src/components/individual-agent-result.tsx",
        "backend/src/diagnosis/reporting.py",
    ):
        raw = (ROOT / relative).read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), relative
        text = raw.decode("utf-8")
        assert not any(marker in text for marker in ("\u00c2", "\u00c3", "\u00e2", "\ufffd")), relative
