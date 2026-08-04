import json
import math
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "instance.json"
PROJECT_COUNT = 150
SEED = 42
RESOURCE_DIMENSIONS = ["cost", "engineering", "staffing", "energy", "risk"]


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


def validate_dependencies(projects):
    ids = {proj["id"] for proj in projects}
    deps = {proj["id"]: proj["deps"] for proj in projects}
    visited = set()
    stack = set()

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

    for proj_id in ids:
        dfs(proj_id)


def generate_projects(seed=SEED):
    rng = random.Random(seed)
    projects = []
    for i in range(PROJECT_COUNT):
        projects.append(
            {
                "id": f"P{i+1}",
                "reward": rng.randint(40, 170),
                "cost": rng.randint(70, 420),
                "engineering": rng.randint(6, 30),
                "staffing": rng.randint(6, 30),
                "energy": rng.randint(4, 22),
                "risk": rng.randint(4, 20),
                "deps": [],
            }
        )
    return projects


def add_dependencies(projects, seed=SEED):
    rng = random.Random(seed + 1)
    project_ids = [proj["id"] for proj in projects]

    chain_starts = [0, 16, 32, 48, 64, 80, 96, 112]
    chain_lengths = [12, 11, 10, 10, 9, 9, 8, 8]
    for start, length in zip(chain_starts, chain_lengths):
        for offset in range(1, length):
            projects[start + offset]["deps"].append(projects[start + offset - 1]["id"])

    shared_roots = [projects[i]["id"] for i in [0, 1, 2, 4, 9]]
    shared_targets = [18, 19, 31, 42, 55, 67, 74, 89, 103, 117]
    for target in shared_targets:
        projects[target]["deps"].append(rng.choice(shared_roots))

    multi_prereq_indices = [14, 25, 38, 53, 66, 79, 93, 106, 118, 131]
    for idx in multi_prereq_indices:
        candidates = [projects[j]["id"] for j in range(max(0, idx - 18), idx) if j != idx]
        dependencies = rng.sample(candidates, k=2)
        projects[idx]["deps"].extend(dependencies)

    for idx in range(120, PROJECT_COUNT):
        if rng.random() < 0.45:
            count = rng.choice([1, 2])
            dependencies = rng.sample([projects[j]["id"] for j in range(0, idx)], k=count)
            projects[idx]["deps"].extend(dependencies)

    for idx in range(35, PROJECT_COUNT):
        if rng.random() < 0.15:
            dep = projects[rng.randint(0, idx - 1)]["id"]
            projects[idx]["deps"].append(dep)

    for proj in projects:
        proj["deps"] = sorted(set(proj["deps"]))

    validate_dependencies(projects)
    return projects


def score_project(project):
    resource_sum = project["cost"] + project["engineering"] + project["staffing"] + project["energy"] + project["risk"]
    return project["reward"] / max(1, resource_sum)


def choose_seed_portfolio(projects, target_size=40):
    deps = {proj["id"]: proj["deps"] for proj in projects}
    candidates = sorted(projects, key=score_project, reverse=True)
    selected = set()
    ordinal = []
    for proj in candidates:
        closure = compute_closure(proj["id"], deps)
        if len(selected | closure) > target_size:
            continue
        selected |= closure
        ordinal.append(proj["id"])
        if len(selected) >= target_size:
            break
    return selected


def compute_resources(project_ids, projects):
    resources = {dim: 0 for dim in RESOURCE_DIMENSIONS}
    project_map = {proj["id"]: proj for proj in projects}
    for proj_id in project_ids:
        proj = project_map[proj_id]
        for dim in RESOURCE_DIMENSIONS:
            resources[dim] += proj[dim]
    return resources


def generate_interactions(projects, seed=SEED + 2):
    rng = random.Random(seed)
    project_ids = [proj["id"] for proj in projects]
    interactions = []
    pairs = []
    for i in range(len(project_ids)):
        for j in range(i + 1, len(project_ids)):
            if (j - i) <= 12 or (i % 10 == 0 and j % 7 == 0) or (i % 9 == 0 and j % 8 == 0):
                pairs.append((project_ids[i], project_ids[j]))
    rng.shuffle(pairs)
    pairs = pairs[:130]
    for a, b in pairs:
        interactions.append(
            {
                "projects": [a, b],
                "type": "synergy" if rng.random() < 0.72 else "conflict",
                "value": rng.randint(9, 34),
            }
        )
    return interactions


def generate_budget(projects, selected_project_ids):
    resources = compute_resources(selected_project_ids, projects)
    budgets = {}
    for dim, value in resources.items():
        budgets[dim] = max(1, int(math.ceil(value * 1.0)))
    return budgets


def count_dependency_depth(projects):
    deps = {proj["id"]: proj["deps"] for proj in projects}
    depths = {}

    def depth(node):
        if node in depths:
            return depths[node]
        if not deps[node]:
            depths[node] = 1
        else:
            depths[node] = 1 + max(depth(dep) for dep in deps[node])
        return depths[node]

    return max(depth(proj["id"]) for proj in projects)


def generate_instance(seed=SEED):
    projects = generate_projects(seed)
    projects = add_dependencies(projects, seed)
    interactions = generate_interactions(projects, seed)
    selected = choose_seed_portfolio(projects, target_size=45)
    budgets = generate_budget(projects, selected)
    instance = {
        "projects": projects,
        "interactions": interactions,
        "budget": budgets,
    }
    return instance


def write_instance(instance):
    OUTPUT_FILE.write_text(json.dumps(instance, indent=2), encoding="utf-8")


def main():
    instance = generate_instance()
    write_instance(instance)
    projects = instance["projects"]
    dependency_count = sum(len(proj["deps"]) for proj in projects)
    depth = count_dependency_depth(projects)
    synergy_count = sum(1 for inter in instance["interactions"] if inter["type"] == "synergy")
    conflict_count = sum(1 for inter in instance["interactions"] if inter["type"] == "conflict")
    print(f"Wrote instance to {OUTPUT_FILE}")
    print(f"projects={len(projects)} dependencies={dependency_count} max_depth={depth}")
    print(f"interactions={len(instance['interactions'])} synergy={synergy_count} conflict={conflict_count}")
    print("budgets=", json.dumps(instance["budget"], indent=2))


if __name__ == "__main__":
    main()
