# Certified Multi-Resource Project Portfolio Optimization

**Project Dynamo Task**

**Category:** Mathematics and Formal Reasoning  
**Sub-category:** Algorithms and Optimization Theory

---

## Overview

This repository contains a Project Dynamo task based on exact project portfolio optimization.

The task is to select a set of projects that maximizes total portfolio value while satisfying multiple resource constraints and project dependency requirements.

Each project has a reward and consumes several limited resources. Some projects also require prerequisite projects, while pairs of projects may have positive synergies or negative conflicts when selected together.

The task is intentionally designed so that finding a feasible portfolio is not enough. A submitted solution must also provide a machine-checkable certificate establishing that the portfolio is globally optimal.

The verifier independently checks both the portfolio and the optimality certificate.

---

## Problem Statement

The goal is to choose a portfolio of projects from a deterministic project instance.

Each project contains:

- Project ID
- Base reward
- Financial cost
- Engineering-hours requirement
- Staffing requirement
- Energy consumption
- Risk value
- Prerequisite projects

A project can only be selected when all of its prerequisites are also selected.

For example, if project `P20` requires `P05`, selecting `P20` requires both:

P05
P20

## Dependencies may form long chains and may also be shared by several projects.

This means that the actual cost and resource requirements of selecting a project can depend on several other projects that must be selected with it.

Resource Constraints

Every portfolio must satisfy five resource limits:

Financial Cost       <= Financial Budget
Engineering Hours    <= Engineering Limit
Staffing             <= Staffing Limit
Energy               <= Energy Limit
Risk                 <= Risk Limit

All resource values and limits are integers.

The verifier independently recomputes all resource totals from the selected project set.

Project Dependencies

For every dependency where project B requires project A, the mathematical constraint is:

x_B <= x_A

where:

x_i = 1

means project i is selected.

This directly enforces prerequisite relationships.

Because dependency relationships can form chains, satisfying all direct dependency constraints also ensures the required transitive dependencies are selected.

The implementation additionally validates the dependency graph and checks the selected portfolio for dependency closure.

Pairwise Interactions

The task contains pairwise interactions between projects.

Synergy

A synergy pair provides an additional integer reward when both projects are selected.

For example:

Project A + Project B
        ↓
Additional bonus

The bonus is applied only when both endpoints are selected.

Conflict

A conflict pair introduces an integer penalty when both projects are selected.

For example:

Project C + Project D
        ↓
Penalty

The penalty is applied only when both projects are selected.

Each interaction is evaluated exactly once.

The implementation prevents interactions from being applied when only one endpoint is selected and prevents double-counting.

Objective Function

The portfolio objective is:

Total Value =
    Sum of selected project rewards
    + Sum of applicable synergy bonuses
    - Sum of applicable conflict penalties

The objective is maximized subject to all dependency and resource constraints.

All final objective calculations use exact integer arithmetic.

Mathematical Formulation

For each project i, the model uses a binary decision variable:

x_i ∈ {0, 1}

where:

x_i = 1

indicates that project i is selected.

For a dependency:

B requires A

the constraint is:

x_B <= x_A

The resource constraints are represented as:

Σ(cost_i × x_i) <= financial_budget

Σ(engineering_i × x_i) <= engineering_limit

Σ(staff_i × x_i) <= staffing_limit

Σ(energy_i × x_i) <= energy_limit

Σ(risk_i × x_i) <= risk_limit

For each pairwise interaction, an auxiliary binary variable can represent whether both projects are selected.

The standard linearization is:

y_AB <= x_A

y_AB <= x_B

y_AB >= x_A + x_B - 1

This allows synergy bonuses and conflict penalties to be incorporated into the objective while keeping the optimization model explicit.

Dataset

The task uses a deterministic synthetic dataset.

The dataset is designed to resemble the type of constrained project portfolio decisions encountered in engineering, infrastructure, technology, manufacturing, and operations planning.

The intended instance contains approximately:

150–200 projects
250–400 dependency relationships
Dependency chains of approximately 8–12 levels
Multiple shared prerequisites
Five resource constraints
Approximately 100–150 pairwise interactions

The resource limits are deliberately constrained so that projects compete with each other for available resources.

The instance contains combinations such as:

High-reward projects with expensive prerequisite chains
Projects with moderate individual rewards but valuable downstream effects
Shared prerequisites used by several projects
Projects competing for engineering capacity
Projects competing for staffing
Projects with high energy requirements
Projects with high risk values
Synergistic project combinations
Conflicting project combinations
Near-optimal alternative portfolios

The dataset is deterministic and does not depend on external services or internet access.

Why the Problem Is Difficult

The difficulty comes from the interaction between several constraints rather than from simply increasing the number of projects.

A project that appears attractive based on its reward alone may become unattractive after accounting for:

Its prerequisite chain
Shared prerequisite costs
Engineering requirements
Staffing requirements
Energy consumption
Risk
Synergy effects
Conflict penalties

The solver therefore has to reason about combinations of projects rather than evaluating projects independently.

Several common approaches can produce incorrect solutions:

Greedy selection by reward
Greedy selection by reward-to-cost ratio
Ignoring transitive dependencies
Counting shared prerequisites incorrectly
Ignoring one of the resource constraints
Applying a synergy when both projects are not selected
Applying a conflict penalty incorrectly
Counting an interaction more than once
Finding a feasible portfolio without establishing optimality
Trusting an optimization solver's OPTIMAL status without an independently verifiable proof

The final requirement for a machine-checkable optimality certificate makes the task substantially stronger than simply asking for the best portfolio.

Reference Optimization Solution

The repository contains a reference solution for solving the optimization instance.

The reference workflow is:

Load deterministic instance
        ↓
Validate input
        ↓
Build optimization model
        ↓
Apply dependency constraints
        ↓
Apply five resource constraints
        ↓
Apply pairwise interactions
        ↓
Optimize total portfolio value
        ↓
Recover optimal portfolio
        ↓
Generate optimality certificate
        ↓
Verify certificate

An exact optimization strategy such as branch-and-bound with LP relaxations can be used to establish the global optimum.

The reference implementation is responsible for calculating:

Selected project IDs
Total portfolio value
Resource totals
Pairwise interaction contributions
Optimality certificate

The expected result is not treated as a hard-coded answer.

Optimality Certificate

A central requirement of this task is a machine-checkable proof of global optimality.

The solution therefore includes an optimality certificate represented as structured JSON.

The certificate describes the branch-and-bound search used to establish that no better feasible portfolio exists.

Certificate nodes contain information required to reconstruct and verify the search, including concepts such as:

Node ID
Parent node
Fixed project decisions
Branch variable
Node status
Upper bound information
Proof information for pruning

A branching node represents the two possible assignments for a selected binary decision:

x_i = 0

and:

x_i = 1

An infeasible branch must contain sufficient information for the verifier to establish that the branch cannot produce a feasible portfolio.

For branches pruned using an LP relaxation, the certificate contains the information required to independently verify the corresponding upper bound.

Where applicable, exact rational dual information is used so that the verifier does not depend on floating-point rounding when checking the bound.

The certificate must establish that every relevant branch is either:

Infeasible, or
Unable to produce a solution with value greater than the submitted portfolio.

Therefore, a solver log or a solver-reported OPTIMAL status is not considered an optimality proof by itself.

Independent Verification

The repository includes an independent verification process.

The verifier reads the original deterministic task data and independently evaluates the submitted solution.

Portfolio Checks

The verifier checks:

Project IDs exist
No project is selected more than once
Dependencies are satisfied
Transitive dependency closure is satisfied
Financial cost is within the budget
Engineering hours are within the limit
Staffing is within the limit
Energy is within the limit
Risk is within the limit
Project rewards are correct
Synergy bonuses are correct
Conflict penalties are correct
Each interaction is counted exactly once
The reported objective matches the independently calculated objective
Certificate Checks

The verifier also checks the optimality certificate.

Depending on the certificate node type, it verifies:

Node structure
Parent-child relationships
Fixed assignments
Branch variables
Required branch coverage
Infeasibility information
LP relaxation information
Exact rational values
Dual feasibility
Dual objective
Upper-bound validity
Search-tree consistency
Global optimality

The verifier does not simply compare the submitted answer against a stored project list.

It also does not rely solely on the reference solver to determine whether the submitted certificate is valid.

Acceptance Criteria

A submission is accepted only when all of the following conditions hold:

Valid project selection
        +
All dependencies satisfied
        +
All five resource limits satisfied
        +
Correct objective calculation
        +
Valid optimality certificate
        +
Proof of global optimality
        =
Accepted solution

A feasible but non-optimal portfolio is rejected.

A portfolio with an incorrect objective value is rejected.

A portfolio violating a dependency is rejected.

A portfolio exceeding any resource limit is rejected.

An invalid or incomplete optimality certificate is rejected.

A certificate that does not establish global optimality is rejected.

Multiple Optimal Solutions

The optimization problem may have more than one globally optimal portfolio.

The verifier therefore does not require the selected project list to match one specific reference selection.

Any portfolio is accepted when it:

Is feasible
Satisfies all dependencies
Satisfies all resource constraints
Achieves the global maximum value
Provides a valid certificate proving that value is optimal

There is no arbitrary project-name tie-breaking requirement.

The important graded property is the globally optimal objective together with a valid proof.

Testing

The repository contains tests for both valid and invalid submissions.

The test coverage includes cases involving:

Valid optimal portfolios
Feasible but non-optimal portfolios
Unknown project IDs
Duplicate project IDs
Missing direct dependencies
Missing transitive dependencies
Financial budget violations
Engineering-hours violations
Staffing violations
Energy violations
Risk violations
Incorrect reward calculations
Incorrect synergy calculations
Incorrect conflict calculations
Double-counted interactions
Incorrect interaction activation
Invalid certificate structure
Duplicate certificate nodes
Invalid parent references
Invalid project assignments
Missing branches
Incorrect branch assignments
Invalid infeasibility claims
Invalid LP certificates
Invalid dual feasibility
Incorrect dual objectives
Invalid upper bounds
Incomplete search certificates
Non-optimal portfolios claiming optimality
Multiple optimal portfolios
Boundary resource cases
Exact integer objective calculations
Reproducibility

The task is deterministic.

The repository does not require:

Internet access
External APIs
Private credentials
Proprietary optimization services

The committed task data produces the same optimization instance across executions.

If an instance-generation script is used, the generation process is deterministic and the final generated instance is stored for reproducible execution.

Repository Structure

The repository contains the main components required to run and verify the task:

.
├── data/
│   └── deterministic task instance
│
├── tests/
│   └── task and verifier tests
│
├── generate_instance.py
├── solver.py
├── verify.py
├── portfolio.json
├── certificate.json
└── README.md
data/

Contains the deterministic optimization instance.

generate_instance.py

Generates or prepares the deterministic project portfolio instance according to the task configuration.

solver.py

Contains the reference optimization logic and solution generation.

portfolio.json

Contains the generated optimal portfolio information.

certificate.json

Contains the machine-checkable optimality certificate.

verify.py

Independently verifies the portfolio and its optimality certificate.

tests/

Contains tests covering valid solutions, invalid solutions, certificate validation, and edge cases.

Running the Task

The exact commands should follow the Project Dynamo repository and container conventions.

Typical local development flow:

python generate_instance.py

Run the reference solution:

python solver.py

Verify the generated solution:

python verify.py

Run the test suite:

pytest

If the Project Dynamo repository provides official validation commands, those commands take precedence over the generic commands above.

Security and Integrity

The task is designed so that a solver cannot obtain acceptance simply by modifying or bypassing the verification process.

The intended verification flow independently reads the task data and checks the submitted output.

The task does not rely on:

External APIs
Internet services
Hidden network resources
Solver logs as proof
A hard-coded expected project list
Floating-point equality for final exact values

The optimality certificate must provide actual evidence supporting the global-optimality claim.

Real-World Motivation

The problem reflects decisions made by professionals involved in operations research, optimization, engineering portfolio planning, infrastructure planning, and technology investment.

In real project portfolios, organizations often have to decide which initiatives can be funded while respecting limited:

Capital
Engineering capacity
Staffing
Energy
Risk tolerance

Projects may also depend on earlier work, and selecting related projects can create additional benefits or conflicts.

A globally optimized portfolio can therefore be significantly more valuable than selecting projects independently or using simple ranking heuristics.

Project Dynamo Classification
Category

Mathematics and Formal Reasoning

Sub-category

Algorithms and Optimization Theory

Justification

The task belongs to Mathematics and Formal Reasoning because the solution requires a formal mathematical model involving variables, constraints, an objective function, and a certificate proving global optimality.

It belongs to Algorithms and Optimization Theory because solving the task involves:

Binary optimization
Dependency-constrained selection
Multiple-resource optimization
Pairwise objective interactions
Branch-and-bound
LP relaxation
Exact optimization
Machine-checkable optimality certification

The task therefore evaluates algorithmic reasoning, optimization methodology, and formal verification rather than simple data processing or information retrieval.

Summary

The task evaluates the complete optimization workflow:

Understand the portfolio problem
            ↓
Model project dependencies
            ↓
Model resource constraints
            ↓
Model synergies and conflicts
            ↓
Find the global optimum
            ↓
Calculate the exact portfolio value
            ↓
Generate an optimality certificate
            ↓
Independently verify the certificate
