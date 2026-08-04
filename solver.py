import argparse
import json
from pathlib import Path
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_FILE = BASE_DIR / "data" / "instance.json"
OUTPUT_PORTFOLIO = BASE_DIR / "portfolio.json"
OUTPUT_CERTIFICATE = BASE_DIR / "certificate.json"


def load_instance(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_instance(instance):
    ids = {proj["id"] for proj in instance["projects"]}
    if len(ids) != len(instance["projects"]):
        raise ValueError("Duplicate project IDs in instance")

    for proj in instance["projects"]:
        for dep in proj["deps"]:
            if dep not in ids:
                raise ValueError(f"Unknown dependency {dep} for project {proj['id']}")

    visited = set()
    stack = set()
    deps = {proj["id"]: proj["deps"] for proj in instance["projects"]}

    def dfs(node):
        if node in stack:
            raise ValueError(f"Dependency cycle detected at {node}")
        if node in visited:
            return
        stack.add(node)
        for dep in deps[node]:
            dfs(dep)
        stack.remove(node)
        visited.add(node)

    for project in ids:
        dfs(project)


def build_graph(instance):
    projects = {proj["id"]: proj for proj in instance["projects"]}
    deps = {proj_id: list(proj["deps"]) for proj_id, proj in projects.items()}
    interactions = instance["interactions"]
    budget = instance["budget"]
    return projects, deps, interactions, budget


def compute_closure(project_id, deps):
    closure = set()

    def dfs(node):
        if node in closure:
            return
        closure.add(node)
        for dep in deps[node]:
            dfs(dep)

    dfs(project_id)
    return closure


def evaluate_selection(selection, projects, deps, interactions):
    selected = set(selection)
    closure = set()
    for proj in selected:
        closure |= compute_closure(proj, deps)

    resources = {"cost": 0, "engineering": 0, "staffing": 0, "energy": 0, "risk": 0}
    reward = 0
    for proj in closure:
        p = projects[proj]
        resources["cost"] += p["cost"]
        resources["engineering"] += p["engineering"]
        resources["staffing"] += p["staffing"]
        resources["energy"] += p["energy"]
        resources["risk"] += p["risk"]
        reward += p["reward"]

    interaction_value = 0
    for inter in interactions:
        a, b = inter["projects"]
        if a in closure and b in closure:
            interaction_value += inter["value"] if inter["type"] == "synergy" else -inter["value"]

    objective = reward + interaction_value
    return closure, resources, objective


def build_milp_model(instance):
    projects, deps, interactions, budget = build_graph(instance)
    project_ids = [proj["id"] for proj in instance["projects"]]
    id_index = {proj_id: idx for idx, proj_id in enumerate(project_ids)}
    n = len(project_ids)
    m = len(interactions)

    c = np.zeros(n + m, dtype=float)
    c[:n] = [-projects[proj_id]["reward"] for proj_id in project_ids]
    for idx, inter in enumerate(interactions):
        value = inter["value"] if inter["type"] == "synergy" else -inter["value"]
        c[n + idx] = -value

    rows = []
    lower = []
    upper = []

    for proj_id, proj in projects.items():
        j = id_index[proj_id]
        for dep in proj["deps"]:
            row = np.zeros(n + m, dtype=float)
            row[j] = 1.0
            row[id_index[dep]] = -1.0
            rows.append(row)
            lower.append(-np.inf)
            upper.append(0.0)

    for key, limit in budget.items():
        row = np.zeros(n + m, dtype=float)
        for proj_id in project_ids:
            row[id_index[proj_id]] = float(projects[proj_id][key])
        rows.append(row)
        lower.append(-np.inf)
        upper.append(float(limit))

    for idx, inter in enumerate(interactions):
        a, b = inter["projects"]
        ai = id_index[a]
        bi = id_index[b]
        yi = n + idx

        row = np.zeros(n + m, dtype=float)
        row[yi] = 1.0
        row[ai] = -1.0
        rows.append(row)
        lower.append(-np.inf)
        upper.append(0.0)

        row = np.zeros(n + m, dtype=float)
        row[yi] = 1.0
        row[bi] = -1.0
        rows.append(row)
        lower.append(-np.inf)
        upper.append(0.0)

        row = np.zeros(n + m, dtype=float)
        row[yi] = 1.0
        row[ai] = -1.0
        row[bi] = -1.0
        rows.append(row)
        lower.append(-1.0)
        upper.append(np.inf)

    A = np.vstack(rows)
    lb = np.array(lower, dtype=float)
    ub = np.array(upper, dtype=float)
    constraints = LinearConstraint(A, lb, ub)

    A_ub = []
    b_ub = []
    A_eq = []
    b_eq = []
    for row_vec, low, high in zip(rows, lower, upper):
        if low == high:
            A_eq.append(row_vec)
            b_eq.append(high)
        elif low == -np.inf and np.isfinite(high):
            A_ub.append(row_vec)
            b_ub.append(high)
        elif np.isfinite(low) and high == np.inf:
            A_ub.append(-row_vec)
            b_ub.append(-low)
        elif low == -np.inf and high == np.inf:
            continue
        else:
            raise RuntimeError("Unsupported constraint type for LP relaxation")

    A_ub = np.vstack(A_ub) if A_ub else None
    b_ub = np.array(b_ub, dtype=float) if b_ub else None
    A_eq = np.vstack(A_eq) if A_eq else None
    b_eq = np.array(b_eq, dtype=float) if b_eq else None

    bounds = Bounds([0.0] * (n + m), [1.0] * (n + m))
    lp_bounds = [(0.0, 1.0)] * (n + m)
    integrality = np.array([1] * n + [0] * m, dtype=int)
    return project_ids, id_index, projects, interactions, budget, c, bounds, constraints, integrality, A_ub, b_ub, A_eq, b_eq, lp_bounds


def compute_lp_relaxation(instance):
    _, _, _, _, _, c, _, _, _, A_ub, b_ub, A_eq, b_eq, lp_bounds = build_milp_model(instance)
    lp_res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=lp_bounds, method="highs")
    if not lp_res.success:
        raise RuntimeError(f"LP relaxation failed: {lp_res.message}")
    return -lp_res.fun


def solve_lp_relaxation(instance, fixed_zero=None, fixed_one=None):
    project_ids, id_index, _, _, _, c, _, _, _, A_ub, b_ub, A_eq, b_eq, lp_bounds = build_milp_model(instance)
    bounds = list(lp_bounds)
    fixed_zero = fixed_zero or []
    fixed_one = fixed_one or []
    for proj_id in fixed_zero:
        bounds[id_index[proj_id]] = (0.0, 0.0)
    for proj_id in fixed_one:
        bounds[id_index[proj_id]] = (1.0, 1.0)
    lp_res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
    return lp_res, project_ids


def is_integer_solution(x, n, tol=1e-8):
    return all(abs(x[i] - round(x[i])) <= tol for i in range(n))


def choose_branch_variable(x, project_ids, tol=1e-8):
    fractional = [(i, abs(x[i] - round(x[i]))) for i in range(len(project_ids))]
    fractional = [(i, d) for i, d in fractional if d > tol]
    if not fractional:
        return None
    fractional.sort(key=lambda pair: pair[1], reverse=True)
    return project_ids[fractional[0][0]]


def build_branch_certificate(instance, best_objective, best_selection):
    projects, deps, interactions, _ = build_graph(instance)
    nodes = []
    next_node_id = 0

    def visit(fixed_zero, fixed_one, parent_id):
        nonlocal next_node_id
        node_id = next_node_id
        next_node_id += 1
        fixed_assignments = {"zero": sorted(fixed_zero), "one": sorted(fixed_one)}
        lp_res, project_ids = solve_lp_relaxation(instance, fixed_zero, fixed_one)

        if not lp_res.success:
            node = {
                "node_id": node_id,
                "parent_id": parent_id,
                "fixed_assignments": fixed_assignments,
                "branch_variable": None,
                "status": "pruned",
                "upper_bound": float("-inf"),
                "proof": {"type": "infeasible"},
            }
            nodes.append(node)
            return

        upper_bound = -lp_res.fun
        n = len(project_ids)
        if is_integer_solution(lp_res.x, n):
            selected_projects = [project_ids[i] for i in range(n) if round(lp_res.x[i]) == 1]
            closure, _, objective = evaluate_selection(selected_projects, projects, deps, interactions)
            node = {
                "node_id": node_id,
                "parent_id": parent_id,
                "fixed_assignments": fixed_assignments,
                "branch_variable": None,
                "status": "optimal" if abs(objective - best_objective) <= 1e-8 else "pruned",
                "upper_bound": upper_bound,
                "proof": {"type": "integer_solution", "value": objective},
            }
            nodes.append(node)
            return

        if upper_bound <= best_objective + 1e-8:
            node = {
                "node_id": node_id,
                "parent_id": parent_id,
                "fixed_assignments": fixed_assignments,
                "branch_variable": None,
                "status": "pruned",
                "upper_bound": upper_bound,
                "proof": {"type": "lp_relaxation", "value": upper_bound},
            }
            nodes.append(node)
            return

        branch_var = choose_branch_variable(lp_res.x, project_ids)
        node = {
            "node_id": node_id,
            "parent_id": parent_id,
            "fixed_assignments": fixed_assignments,
            "branch_variable": branch_var,
            "status": "branch",
            "upper_bound": upper_bound,
            "proof": {"type": "lp_relaxation", "value": upper_bound},
        }
        nodes.append(node)
        visit(fixed_zero + [branch_var], fixed_one, node_id)
        visit(fixed_zero, fixed_one + [branch_var], node_id)

    visit([], [], None)
    return {
        "root": 0,
        "nodes": nodes,
        "best_objective": best_objective,
        "best_selection": sorted(best_selection),
    }


def solve_exact(instance, time_limit=180.0):
    project_ids, _, projects, interactions, _, c, bounds, constraints, integrality, _, _, _, _, _ = build_milp_model(instance)
    lp_upper_bound = compute_lp_relaxation(instance)

    mip_res = milp(
        c,
        bounds=bounds,
        constraints=constraints,
        integrality=integrality,
        options={"presolve": True, "time_limit": float(time_limit), "mip_rel_gap": 0.0},
    )
    if not mip_res.success:
        raise RuntimeError(f"MILP solve did not converge: {mip_res.message}")

    selected_projects = [project_ids[i] for i, x in enumerate(mip_res.x[: len(project_ids)]) if round(x) == 1]
    closure, resources, objective = evaluate_selection(selected_projects, projects, {proj_id: proj["deps"] for proj_id, proj in projects.items()}, interactions)
    if abs(objective + mip_res.fun) > 1e-6:
        raise RuntimeError("Computed objective does not match MILP result")

    certificate = build_branch_certificate(instance, objective, selected_projects)
    certificate["resources"] = resources
    certificate["root_upper_bound"] = lp_upper_bound
    best = {
        "objective": objective,
        "selection": sorted(selected_projects),
        "resources": resources,
    }
    return best, certificate


def write_output(portfolio, certificate, portfolio_path=None, certificate_path=None):
    portfolio_file = Path(portfolio_path) if portfolio_path is not None else OUTPUT_PORTFOLIO
    certificate_file = Path(certificate_path) if certificate_path is not None else OUTPUT_CERTIFICATE
    portfolio_file.write_text(json.dumps(portfolio, indent=2), encoding="utf-8")
    certificate_file.write_text(json.dumps(certificate, indent=2), encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="Solve a project portfolio optimization instance and emit a certificate.")
    parser.add_argument("--instance", default=str(INSTANCE_FILE), help="Path to instance JSON file")
    parser.add_argument("--portfolio", default=str(OUTPUT_PORTFOLIO), help="Path to write selected portfolio JSON")
    parser.add_argument("--certificate", default=str(OUTPUT_CERTIFICATE), help="Path to write certificate JSON")
    parser.add_argument("--time-limit", type=float, default=180.0, help="Time limit for mixed-integer solve")
    return parser.parse_args()


def main():
    args = parse_args()
    instance = load_instance(Path(args.instance))
    validate_instance(instance)
    best, certificate = solve_exact(instance, time_limit=args.time_limit)
    portfolio = {
        "selected_projects": best["selection"],
        "objective": best["objective"],
        "resources": best["resources"],
    }
    write_output(portfolio, certificate, portfolio_path=args.portfolio, certificate_path=args.certificate)
    print(f"Built portfolio at {args.portfolio} and certificate at {args.certificate}.")


if __name__ == "__main__":
    main()
