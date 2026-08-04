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
    if "nodes" not in data or "best_objective" not in data or "best_selection" not in data or "root" not in data:
        raise VerificationError("Certificate JSON must contain nodes, root, best_selection, and best_objective")
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
    if "root" not in certificate:
        raise VerificationError("Certificate must include root")
    if "best_selection" not in certificate:
        raise VerificationError("Certificate must include best_selection")
    if "best_objective" not in certificate:
        raise VerificationError("Certificate must include best_objective")

    nodes = certificate["nodes"]
    if not isinstance(nodes, list) or not nodes:
        raise VerificationError("Certificate nodes must be a non-empty list")
    node_ids = {node["node_id"] for node in nodes}
    if len(node_ids) != len(nodes):
        raise VerificationError("Certificate node IDs must be unique")
    for node in nodes:
        if "parent_id" not in node or "fixed_assignments" not in node or "status" not in node:
            raise VerificationError("Each certificate node must include parent_id, fixed_assignments, and status")

    if certificate.get("root_upper_bound") is not None and not isinstance(certificate["root_upper_bound"], (int, float)):
        raise VerificationError("root_upper_bound must be numeric")

    project_ids = {proj["id"] for proj in instance["projects"]}
    if sorted(certificate["best_selection"]) != sorted(portfolio["selected_projects"]):
        raise VerificationError("Certificate best_selection does not match portfolio selected_projects")
    if certificate["best_objective"] != portfolio["objective"]:
        raise VerificationError("Certificate best objective does not match portfolio objective")

    branch_children = {}
    status_allowed = {"branch", "pruned", "optimal"}
    for node in nodes:
        if node["status"] not in status_allowed:
            raise VerificationError(f"Invalid node status {node['status']}")
        if node["parent_id"] is not None and node["parent_id"] not in node_ids:
            raise VerificationError(f"Invalid parent_id {node['parent_id']}")
        if node["node_id"] == certificate["root"] and node["parent_id"] is not None:
            raise VerificationError("Root node must have parent_id set to None")
        fixed = node["fixed_assignments"]
        if not isinstance(fixed, dict):
            raise VerificationError("fixed_assignments must be a dict")
        if "zero" not in fixed or "one" not in fixed:
            raise VerificationError("fixed_assignments must contain zero and one lists")
        if not isinstance(fixed["zero"], list) or not isinstance(fixed["one"], list):
            raise VerificationError("fixed_assignments zero and one must be lists")
        if len(set(fixed["zero"])) != len(fixed["zero"]) or len(set(fixed["one"])) != len(fixed["one"]):
            raise VerificationError("fixed_assignments lists must not contain duplicates")
        if set(fixed["zero"]) & set(fixed["one"]):
            raise VerificationError("fixed_assignments cannot fix a variable to both zero and one")
        if any(proj not in project_ids for proj in fixed["zero"] + fixed["one"]):
            raise VerificationError("Certificate contains invalid project IDs in fixed_assignments")

        if node["status"] == "branch":
            branch_var = node.get("branch_variable")
            if branch_var is None:
                raise VerificationError("Branch node must declare branch_variable")
            if branch_var not in project_ids:
                raise VerificationError(f"Branch variable {branch_var} is not a valid project id")
            if branch_var in fixed["zero"] or branch_var in fixed["one"]:
                raise VerificationError("Branch variable cannot be fixed at a branch node")
            if "upper_bound" not in node:
                raise VerificationError("Branch node must include upper_bound")
            if "proof" not in node:
                raise VerificationError("Branch node must include proof")
            if node["proof"].get("type") != "lp_relaxation":
                raise VerificationError("Branch node proof must be lp_relaxation")
            if not isinstance(node["proof"].get("value"), (int, float)):
                raise VerificationError("Branch node proof value must be numeric")
        else:
            if node.get("branch_variable") is not None:
                raise VerificationError("Non-branch node must not declare branch_variable")
            if "upper_bound" not in node:
                raise VerificationError(f"{node['status'].capitalize()} node must include upper_bound")
            if "proof" not in node:
                raise VerificationError(f"{node['status'].capitalize()} node must include proof")
            proof_type = node["proof"].get("type")
            if node["status"] == "pruned":
                if proof_type not in {"lp_relaxation", "infeasible", "integer_solution"}:
                    raise VerificationError("Pruned node proof must be lp_relaxation, infeasible, or integer_solution")
                if proof_type == "lp_relaxation":
                    if not isinstance(node["proof"].get("value"), (int, float)):
                        raise VerificationError("Pruned node proof value must be numeric")
                    if node["upper_bound"] != node["proof"].get("value"):
                        raise VerificationError("Pruned node upper_bound must equal lp_relaxation proof value")
                    if node["upper_bound"] > certificate["best_objective"] + 1e-8:
                        raise VerificationError("Pruned node upper_bound must not exceed best objective")
                if proof_type == "integer_solution":
                    if not isinstance(node["proof"].get("value"), (int, float)):
                        raise VerificationError("Pruned node proof value must be numeric")
                    if node["upper_bound"] != node["proof"].get("value"):
                        raise VerificationError("Pruned node upper_bound must equal integer_solution proof value")
                    if node["proof"].get("value") > certificate["best_objective"] + 1e-8:
                        raise VerificationError("Pruned node integer_solution proof value must not exceed best objective")
            if node["status"] == "optimal":
                if proof_type != "integer_solution":
                    raise VerificationError("Optimal node proof must be integer_solution")
                if not isinstance(node["proof"].get("value"), (int, float)):
                    raise VerificationError("Optimal node proof value must be numeric")
                if abs(node["proof"].get("value") - certificate["best_objective"]) > 1e-8:
                    raise VerificationError("Optimal node proof value must equal best objective")
                if abs(node["upper_bound"] - certificate["best_objective"]) > 1e-8:
                    raise VerificationError("Optimal node upper_bound must equal best objective")

        branch_children.setdefault(node["node_id"], [])
        if node["parent_id"] is not None:
            branch_children[node["parent_id"]].append(node["node_id"])

    if certificate["root"] not in node_ids:
        raise VerificationError("Certificate root must refer to a valid node")
    root_node = next(node for node in nodes if node["node_id"] == certificate["root"])
    if root_node["parent_id"] is not None:
        raise VerificationError("Certificate root node parent_id must be None")

    optimal_found = False
    for node_id, children in branch_children.items():
        node = next(n for n in nodes if n["node_id"] == node_id)
        if node["status"] == "branch":
            if len(children) != 2:
                raise VerificationError("Branch node must have exactly two children")
            child_nodes = [next(n for n in nodes if n["node_id"] == child_id) for child_id in children]
            branch_var = node["branch_variable"]
            child_assignments = [set(child["fixed_assignments"]["one"]) | set(child["fixed_assignments"]["zero"]) for child in child_nodes]
            parent_assign = set(node["fixed_assignments"]["one"]) | set(node["fixed_assignments"]["zero"])
            for assignments in child_assignments:
                if not parent_assign.issubset(assignments):
                    raise VerificationError("Child node does not inherit parent fixed assignments")
                if len(assignments) != len(parent_assign) + 1:
                    raise VerificationError("Child node must fix exactly one additional variable compared to parent")
                added = assignments - parent_assign
                if len(added) != 1 or branch_var not in added:
                    raise VerificationError("Branch children must differ from parent by exactly the branch_variable")
            if branch_var in child_nodes[0]["fixed_assignments"]["one"] and branch_var in child_nodes[1]["fixed_assignments"]["one"]:
                raise VerificationError("Both branch children cannot fix branch_variable to one")
            if branch_var in child_nodes[0]["fixed_assignments"]["zero"] and branch_var in child_nodes[1]["fixed_assignments"]["zero"]:
                raise VerificationError("Both branch children cannot fix branch_variable to zero")
        elif node["status"] in {"pruned", "optimal"}:
            if children:
                raise VerificationError(f"Leaf node {node_id} must not have children")
        if node["status"] == "optimal":
            optimal_found = True

    if not optimal_found:
        root_upper_bound = certificate.get("root_upper_bound")
        if root_upper_bound is None or not isinstance(root_upper_bound, (int, float)):
            raise VerificationError("Certificate must contain at least one optimal leaf or a numeric root_upper_bound")
        if root_upper_bound > certificate["best_objective"] + 1e-8:
            raise VerificationError("Certificate must contain at least one optimal leaf or a root_upper_bound no greater than best objective")
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
