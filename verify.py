import argparse
import json
from pathlib import Path
from scipy.optimize import linprog

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_FILE = BASE_DIR / "data" / "instance.json"


class VerificationError(Exception):
    pass


def load_instance(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_portfolio(path: Path):
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if "selected_projects" not in data or "objective" not in data or "resources" not in data:
        raise VerificationError("Portfolio JSON must contain selected_projects, objective, and resources")
    if not isinstance(data["selected_projects"], list):
        raise VerificationError("selected_projects must be a list")
    return data


def parse_certificate(path: Path):
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if "nodes" not in data or "best_objective" not in data:
        raise VerificationError("Certificate JSON must contain nodes and best_objective")
    return data


def validate_instance(instance):
    ids = {proj["id"] for proj in instance["projects"]}
    if len(ids) != len(instance["projects"]):
        raise VerificationError("Duplicate project IDs in instance")
    deps = {proj["id"]: proj["deps"] for proj in instance["projects"]}
    for proj in instance["projects"]:
        for dep in proj["deps"]:
            if dep not in ids:
                raise VerificationError(f"Unknown dependency {dep} for project {proj['id']}")
    visited = set()
    stack = set()

    def dfs(node):
        if node in stack:
            raise VerificationError(f"Dependency cycle detected at {node}")
        if node in visited:
            return
        stack.add(node)
        for dep in deps[node]:
            dfs(dep)
        stack.remove(node)
        visited.add(node)

    for proj_id in ids:
        dfs(proj_id)
    return deps


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


def evaluate_portfolio(portfolio, instance):
    ids = {proj["id"] for proj in instance["projects"]}
    projects = {proj["id"]: proj for proj in instance["projects"]}
    selected = portfolio["selected_projects"]

    if len(set(selected)) != len(selected):
        raise VerificationError("Duplicate project IDs in portfolio")
    if any(proj not in ids for proj in selected):
        raise VerificationError("Unknown project IDs in portfolio")

    deps = validate_instance(instance)
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
    for inter in instance["interactions"]:
        a, b = inter["projects"]
        if a in closure and b in closure:
            interaction_value += inter["value"] if inter["type"] == "synergy" else -inter["value"]

    objective = reward + interaction_value
    if objective != portfolio["objective"]:
        raise VerificationError(f"Portfolio objective {portfolio['objective']} does not match computed {objective}")
    if resources != portfolio["resources"]:
        raise VerificationError("Portfolio resource totals are incorrect")
    if any(resources[k] > instance["budget"][k] for k in resources):
        raise VerificationError("Portfolio violates resource limits")

    return closure, resources, objective


def validate_certificate(certificate, instance, portfolio):
    nodes = certificate["nodes"]
    if not isinstance(nodes, list) or not nodes:
        raise VerificationError("Certificate nodes must be a non-empty list")
    node_ids = {node["node_id"] for node in nodes}
    if len(node_ids) != len(nodes):
        raise VerificationError("Certificate node IDs must be unique")
    for node in nodes:
        if "parent_id" not in node or "fixed_assignments" not in node or "status" not in node:
            raise VerificationError("Each certificate node must include parent_id, fixed_assignments, and status")
        if node["parent_id"] is not None and node["parent_id"] not in node_ids:
            raise VerificationError(f"Invalid parent_id {node['parent_id']}")
        fixed = node["fixed_assignments"]
        if any(x in fixed["zero"] and x in fixed["one"] for x in fixed["zero"] + fixed["one"]):
            raise VerificationError("Fixed assignments conflict in node")

    project_ids = {proj["id"] for proj in instance["projects"]}
    for node in nodes:
        fixed_zero = node["fixed_assignments"]["zero"]
        fixed_one = node["fixed_assignments"]["one"]
        if any(proj not in project_ids for proj in fixed_zero + fixed_one):
            raise VerificationError("Certificate contains invalid project IDs in fixed_assignments")
        if node["status"] == "pruned":
            if "upper_bound" not in node:
                raise VerificationError("Pruned node must include upper_bound")
            if "proof" not in node:
                raise VerificationError("Pruned node must include proof")
            if node["proof"].get("type") not in {"lp_relaxation", "infeasible"}:
                raise VerificationError("Pruned node proof must be either lp_relaxation or infeasible")
            if node["proof"].get("type") == "lp_relaxation" and not isinstance(node["proof"].get("value"), (int, float)):
                raise VerificationError("Pruned node proof value must be numeric")
        if node["status"] == "optimal":
            if "upper_bound" not in node:
                raise VerificationError("Optimal node must include upper_bound")
            if node["upper_bound"] < portfolio["objective"]:
                raise VerificationError("Upper bound in optimal node is lower than reported objective")
    return True


def verify_branch_structure(certificate):
    nodes = certificate["nodes"]
    tree = {node["node_id"]: node for node in nodes}
    for node in nodes:
        parent_id = node["parent_id"]
        if parent_id is not None and parent_id not in tree:
            raise VerificationError(f"Certificate node parent_id {parent_id} does not exist")
        if node["status"] == "branch" and node["branch_variable"] is None:
            raise VerificationError("Branch node must declare branch_variable")
    return True


def main():
    parser = argparse.ArgumentParser(description="Verify portfolio and certificate")
    parser.add_argument("portfolio")
    parser.add_argument("certificate")
    args = parser.parse_args()

    instance = load_instance(INSTANCE_FILE)
    portfolio = parse_portfolio(Path(args.portfolio))
    certificate = parse_certificate(Path(args.certificate))

    closure, resources, objective = evaluate_portfolio(portfolio, instance)
    if objective != certificate["best_objective"]:
        raise VerificationError("Certificate best objective does not match portfolio objective")
    validate_certificate(certificate, instance, portfolio)
    verify_branch_structure(certificate)
    print("VERIFIED")


if __name__ == "__main__":
    main()
