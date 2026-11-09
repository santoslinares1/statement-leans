from pathlib import Path

from statementlens.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


def test_cli_facts_writes_memo(tmp_path: Path, capsys) -> None:
    out = tmp_path / "out"
    code = main(
        [
            "STRESS",
            "--facts",
            str(FIXTURES / "stressco.companyfacts.json"),
            "--name",
            "StressCo Inc.",
            "-o",
            str(out),
        ]
    )
    assert code == 0
    memo = (out / "stress_analyst_memo.md").read_text(encoding="utf-8")
    assert "StressCo Inc. (STRESS)" in memo
    assert "Receivables growing faster than sales" in memo
    captured = capsys.readouterr()
    assert "Wrote memo" in captured.out
