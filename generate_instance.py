import json
import random
from pathlib import Path

random.seed(20260804)

categories = [
    "Core", "Platform", "Service", "Analytics", "Security", "Operations", "Customer", "Research", "Infrastructure"
]

projects = []


def mk_project(name, cost, engineering, staffing, energy, risk, reward, deps=None):
    return {
        "id": name,
        "cost": cost,
        "engineering": engineering,
        "staffing": staffing,
        "energy": energy,
        "risk": risk,
        "reward": reward,
        "deps": deps or []
    }

roots = []
for cat in categories:
    root_name = f"{cat}Core"
    roots.append(root_name)
    projects.append(mk_project(root_name, cost=90, engineering=80, staffing=5, energy=45, risk=8, reward=95))

chains = []
for root in roots:
    prev = root
    chain = [root]
    length = random.randint(8, 11)
    for i in range(length):
        name = f"{root}_Layer{i+1}"
        cost = random.randint(40, 80)
        engineering = random.randint(40, 90)
        staffing = random.randint(2, 6)
        energy = random.randint(15, 45)
        risk = random.randint(3, 10)
        reward = random.randint(50, 115)
        projects.append(mk_project(name, cost, engineering, staffing, energy, risk, reward, [prev]))
        prev = name
        chain.append(name)
    chains.append(chain)

shared_modules = [
    "CorePlatform", "NetworkFabric", "DataHub", "SecurityLayer", "ComplianceEngine",
    "AuditLedger", "TelemetryBus", "IdentityKernel", "GovernanceMesh", "ResourceOrchestrator"
]
for module in shared_modules:
    projects.append(mk_project(module, cost=random.randint(50, 90), engineering=random.randint(55, 90), staffing=random.randint(3, 8), energy=random.randint(18, 40), risk=random.randint(5, 12), reward=random.randint(45, 95), deps=[]))

for i in range(len(chains)):
    for j in range(i + 1, len(chains)):
        if random.random() < 0.6:
            source = random.choice(chains[i][2:-1])
            target = random.choice(chains[j][3:])
            for project in projects:
                if project["id"] == target and source not in project["deps"]:
                    project["deps"].append(source)
                    break

shared_assignments = {
    "CorePlatform": ["PlatformCore_Layer3", "ServiceCore_Layer2", "InfrastructureCore_Layer4"],
    "NetworkFabric": ["InfrastructureCore_Layer5", "SecurityCore_Layer3"],
    "DataHub": ["AnalyticsCore_Layer4", "ResearchCore_Layer5", "CustomerCore_Layer3"],
    "SecurityLayer": ["SecurityCore_Layer3", "OperationsCore_Layer4", "PlatformCore_Layer5"],
    "ComplianceEngine": ["CustomerCore_Layer4", "OperationsCore_Layer3", "AnalyticsCore_Layer5"],
    "TelemetryBus": ["AnalyticsCore_Layer6", "ResearchCore_Layer4", "InfrastructureCore_Layer6"],
    "IdentityKernel": ["ServiceCore_Layer6"],
    "GovernanceMesh": ["CustomerCore_Layer5"],
    "ResourceOrchestrator": ["OperationsCore_Layer5", "InfrastructureCore_Layer7"],
}
for module, targets in shared_assignments.items():
    for target in targets:
        for project in projects:
            if project["id"] == target and module not in project["deps"]:
                project["deps"].append(module)
                break

for idx, root in enumerate(roots):
    name = f"{root}_Partner"
    avail = chains[idx][3:]
    deps = random.sample(avail, min(3, len(avail)))
    cost = random.randint(70, 100)
    engineering = random.randint(60, 95)
    staffing = random.randint(4, 8)
    energy = random.randint(25, 55)
    risk = random.randint(7, 14)
    reward = random.randint(90, 135)
    projects.append(mk_project(name, cost, engineering, staffing, energy, risk, reward, deps))

for k in range(1, 17):
    selected = random.sample(roots, 3)
    deps = [f"{s}_Layer{random.randint(2, 7)}" for s in selected]
    name = f"Integration{k}"
    cost = random.randint(70, 110)
    engineering = random.randint(60, 100)
    staffing = random.randint(5, 9)
    energy = random.randint(30, 70)
    risk = random.randint(8, 14)
    reward = random.randint(100, 150)
    projects.append(mk_project(name, cost, engineering, staffing, energy, risk, reward, deps))

for p in range(35):
    base = random.choice(projects)["id"]
    name = f"Feature{p+1}"
    cost = random.randint(25, 55)
    engineering = random.randint(20, 45)
    staffing = random.randint(1, 5)
    energy = random.randint(12, 32)
    risk = random.randint(2, 7)
    reward = random.randint(30, 80)
    projects.append(mk_project(name, cost, engineering, staffing, energy, risk, reward, [base]))

for q in range(25):
    root = random.choice(chains)
    ancestor = random.choice(root[2:])
    name = f"Deep{q+1}"
    cost = random.randint(90, 130)
    engineering = random.randint(80, 120)
    staffing = random.randint(6, 10)
    energy = random.randint(45, 75)
    risk = random.randint(9, 15)
    reward = random.randint(120, 170)
    projects.append(mk_project(name, cost, engineering, staffing, energy, risk, reward, [ancestor]))

extra_modules = [
    "AuditDashboard", "IncidentResponse", "PolicyOrchestrator", "SyntheticMonitoring",
    "DecisionAssistant", "ResourcePlanner", "MarketForecaster", "SupplyChainSync",
    "IntegrationHub", "OperationalInsights", "StakeholderPortal", "FieldOperations",
    "KnowledgeBase", "TrainingCenter", "LegacyAdapter", "CustomerAnalytics",
    "ResilienceEngine", "EnergyOptimizer"
]
for name in extra_modules:
    deps = random.sample([p["id"] for p in projects if len(p["deps"]) > 0], k=3)
    cost = random.randint(50, 95)
    engineering = random.randint(50, 95)
    staffing = random.randint(4, 9)
    energy = random.randint(20, 50)
    risk = random.randint(6, 12)
    reward = random.randint(60, 115)
    projects.append(mk_project(name, cost, engineering, staffing, energy, risk, reward, deps))

if len(projects) > 185:
    deps = {p["id"]: p["deps"] for p in projects}

    def closure_of_ids(ids):
        closure = set(ids)
        changed = True
        while changed:
            changed = False
            for proj, project_deps in deps.items():
                if proj in closure:
                    for dep in project_deps:
                        if dep not in closure:
                            closure.add(dep)
                            changed = True
        return closure

    def project_closure_size(project_id):
        closure = set()

        def dfs(node):
            if node in closure:
                return
            closure.add(node)
            for dep in deps[node]:
                dfs(dep)

        dfs(project_id)
        return closure

    project_ids = [p["id"] for p in projects]
    keep_ids = set([p for p in project_ids if p.endswith('Core')])
    keep_ids |= set(shared_modules)
    keep_ids |= set(shared_assignments.keys())
    keep_ids |= set(extra_modules)
    keep_ids |= set([f"Integration{i}" for i in range(1, 17)])
    keep_ids |= set([f"Feature{i}" for i in range(1, 21)])
    keep_ids |= set([f"Deep{i}" for i in range(1, 16)])
    keep_ids = closure_of_ids(keep_ids)

    candidates = [proj for proj in sorted(project_ids) if proj not in keep_ids]
    current_closure = set(keep_ids)
    for proj in candidates:
        proj_closure = project_closure_size(proj)
        delta = proj_closure - current_closure
        if len(current_closure) + len(delta) <= 175:
            current_closure |= proj_closure
    if len(current_closure) < 175:
        for proj in candidates:
            if proj in current_closure:
                continue
            proj_closure = project_closure_size(proj)
            delta = proj_closure - current_closure
            if len(current_closure) + len(delta) <= 180:
                current_closure |= proj_closure
                if len(current_closure) >= 175:
                    break
    projects = [p for p in projects if p["id"] in current_closure]

project_ids = [p["id"] for p in projects]
print("project count", len(projects))

pairs = set()
interactions = []
while len(interactions) < 145:
    a, b = random.sample(project_ids, 2)
    pair = tuple(sorted((a, b)))
    if pair in pairs:
        continue
    pairs.add(pair)
    if random.random() < 0.58:
        interactions.append({"type": "synergy", "projects": [a, b], "value": random.randint(12, 40)})
    else:
        interactions.append({"type": "conflict", "projects": [a, b], "value": random.randint(10, 35)})

projects.sort(key=lambda p: p["id"])
interactions.sort(key=lambda x: (x["type"], x["projects"][0], x["projects"][1]))

instance = {
    "budget": {
        "cost": 4300,
        "engineering": 3900,
        "staffing": 520,
        "energy": 3200,
        "risk": 290
    },
    "projects": projects,
    "interactions": interactions
}

Path("data").mkdir(exist_ok=True)
Path("data/instance.json").write_text(json.dumps(instance, indent=2), encoding="utf-8")
print("written instance with", len(projects), "projects and", len(interactions), "interactions")
