import json
from pathlib import Path
import pytest

from verify import parse_certificate, parse_portfolio, VerificationError, validate_certificate, evaluate_portfolio, verify_branch_structure

TEST_DIR = Path(__file__).resolve().parent
DATA_DIR = TEST_DIR.parent / "data"


def load_instance():
    with (DATA_DIR / "instance.json").open("r", encoding="utf-8") as f:
        return json.load(f)


def test_parse_portfolio_valid(tmp_path):
    portfolio = {"selected_projects": ["P1"], "objective": 50, "resources": {"cost": 100, "engineering": 10, "staffing": 10, "energy": 8, "risk": 5}}
    p = tmp_path / "portfolio.json"
    p.write_text(json.dumps(portfolio), encoding="utf-8")
    parsed = parse_portfolio(p)
    assert parsed["selected_projects"] == ["P1"]


def test_parse_certificate_valid(tmp_path):
    certificate = {"nodes": [{"node_id": 0, "parent_id": None, "fixed_assignments": {"zero": [], "one": []}, "status": "optimal", "upper_bound": 10, "proof": {"type": "integer_solution", "value": 10}}], "best_objective": 10, "best_selection": [], "root": 0}
    p = tmp_path / "certificate.json"
    p.write_text(json.dumps(certificate), encoding="utf-8")
    parsed = parse_certificate(p)
    assert parsed["best_objective"] == 10


def test_validate_certificate_invalid_parent(tmp_path):
    certificate = {"nodes": [{"node_id": 0, "parent_id": 5, "fixed_assignments": {"zero": [], "one": []}, "status": "optimal", "upper_bound": 10, "proof": {"type": "integer_solution", "value": 10}}], "best_objective": 10, "best_selection": [], "root": 0}
    with pytest.raises(VerificationError):
        validate_certificate(certificate, load_instance(), {"selected_projects": [], "objective": 0, "resources": {"cost": 0, "engineering": 0, "staffing": 0, "energy": 0, "risk": 0}})


def test_validate_certificate_missing_root(tmp_path):
    certificate = {"nodes": [{"node_id": 0, "parent_id": None, "fixed_assignments": {"zero": [], "one": []}, "status": "optimal", "upper_bound": 10, "proof": {"type": "integer_solution", "value": 10}}], "best_objective": 10, "best_selection": []}
    with pytest.raises(VerificationError):
        validate_certificate(certificate, load_instance(), {"selected_projects": [], "objective": 0, "resources": {"cost": 0, "engineering": 0, "staffing": 0, "energy": 0, "risk": 0}})


def test_validate_certificate_best_selection_mismatch(tmp_path):
    certificate = {
        "nodes": [{"node_id": 0, "parent_id": None, "fixed_assignments": {"zero": [], "one": []}, "status": "optimal", "upper_bound": 10, "proof": {"type": "integer_solution", "value": 10}}],
        "best_objective": 10,
        "best_selection": ["P1"],
        "root": 0,
    }
    portfolio = {"selected_projects": ["P2"], "objective": 10, "resources": {"cost": 0, "engineering": 0, "staffing": 0, "energy": 0, "risk": 0}}
    with pytest.raises(VerificationError):
        validate_certificate(certificate, load_instance(), portfolio)


def test_branch_certificate_structure():
    certificate = {
        "nodes": [
            {"node_id": 0, "parent_id": None, "fixed_assignments": {"zero": [], "one": []}, "branch_variable": "P1", "status": "branch", "upper_bound": 100, "proof": {"type": "lp_relaxation", "value": 100}},
            {"node_id": 1, "parent_id": 0, "fixed_assignments": {"zero": ["P1"], "one": []}, "branch_variable": None, "status": "pruned", "upper_bound": 50, "proof": {"type": "lp_relaxation", "value": 50}},
            {"node_id": 2, "parent_id": 0, "fixed_assignments": {"zero": [], "one": ["P1"]}, "branch_variable": None, "status": "optimal", "upper_bound": 80, "proof": {"type": "integer_solution", "value": 80}},
        ],
        "best_objective": 80,
    }
    verify_branch_structure(certificate)


def test_evaluate_portfolio_sanity():
    instance = load_instance()
    portfolio = {"selected_projects": [instance["projects"][0]["id"]], "objective": 0, "resources": {"cost": 0, "engineering": 0, "staffing": 0, "energy": 0, "risk": 0}}
    with pytest.raises(VerificationError):
        evaluate_portfolio(portfolio, instance)


def test_validate_certificate_on_actual_solution(tmp_path):
    from solver import main as solver_main

    portfolio_path = tmp_path / "portfolio.json"
    certificate_path = tmp_path / "certificate.json"
    data_path = Path("data") / "instance.json"
    # run solver with explicit output files to get a real certificate
    import subprocess

    subprocess.run(["python", "solver.py", "--instance", str(data_path), "--portfolio", str(portfolio_path), "--certificate", str(certificate_path)], check=True)

    portfolio = parse_portfolio(portfolio_path)
    certificate = parse_certificate(certificate_path)
    instance = load_instance()
    closure, resources, objective = evaluate_portfolio(portfolio, instance)
    assert objective == portfolio["objective"]
    validate_certificate(certificate, instance, portfolio)
    verify_branch_structure(certificate)
