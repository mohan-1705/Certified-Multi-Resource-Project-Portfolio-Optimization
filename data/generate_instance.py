import json
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "instance.json"

PROJECT_COUNT = 25
RESOURCE_BUDGETS = {
    "cost": 2200,
    "engineering": 125,
    "staffing": 120,
    "energy": 105,
    "risk": 90,
}


def deterministic_random(seed):
    rng = random.Random(seed)
    while True:
        yield rng.random()


def generate_projects(seed=42):
    rng = random.Random(seed)
    projects = []
    for i in range(PROJECT_COUNT):
        proj_id = f"P{i+1}"
        projects.append(
            {
                "id": proj_id,
                "reward": rng.randint(25, 120),
                "cost": rng.randint(80, 340),
                "engineering": rng.randint(5, 24),
                "staffing": rng.randint(5, 24),
                "energy": rng.randint(4, 18),
                "risk": rng.randint(3, 16),
                "deps": [],
            }
        )

    dependencies = [(0, 1), (1, 2), (3, 4), (2, 5), (5, 6), (7, 8), (8, 9), (10, 11), (11, 12), (12, 13)]
    for a, b in dependencies:
        projects[b]["deps"].append(projects[a]["id"])

    for source, target in [(14, 15), (15, 16), (14, 17), (17, 18)]:
        projects[target]["deps"].append(projects[source]["id"])

    for i in [19, 20, 21, 22, 23, 24]:
        if rng.random() < 0.4:
            dep = rng.choice([j for j in range(i) if j != i])
            projects[i]["deps"].append(projects[dep]["id"])

    for proj in projects:
        proj["deps"] = sorted(set(proj["deps"]))

    return projects


def generate_interactions(seed=42):
    rng = random.Random(seed + 1)
    interactions = []
    for a, b in [(0, 2), (1, 3), (4, 5), (5, 6), (7, 13), (8, 9), (10, 14), (12, 15), (16, 17), (18, 20), (19, 21), (22, 23), (23, 24)]:
        if rng.random() < 0.9:
            interactions.append(
                {
                    "projects": [f"P{a+1}", f"P{b+1}"],
                    "type": "synergy" if rng.random() < 0.7 else "conflict",
                    "value": rng.randint(8, 28),
                }
            )
    return interactions


def generate_instance(seed=42):
    projects = generate_projects(seed)
    interactions = generate_interactions(seed)
    instance = {
        "projects": projects,
        "interactions": interactions,
        "budget": RESOURCE_BUDGETS,
    }
    return instance


def write_instance(instance):
    OUTPUT_FILE.write_text(json.dumps(instance, indent=2), encoding="utf-8")


def main():
    instance = generate_instance()
    write_instance(instance)
    print(f"Wrote instance to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
