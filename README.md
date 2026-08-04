# Certified Multi-Resource Project Portfolio Optimization

**Project Dynamo Task**

**Category:** Mathematics and Formal Reasoning  
**Sub-category:** Algorithms and Optimization Theory

## Overview

This task models a realistic project portfolio selection problem.

The goal is to select the best possible set of projects while working within limited financial, engineering, staffing, energy, and risk resources. Projects also have dependencies, meaning that some projects can only be selected when their required prerequisite projects are selected.

The task goes beyond finding a high-value portfolio. The submitted solution must also provide a machine-checkable certificate proving that the selected portfolio is globally optimal.

A solver's `OPTIMAL` status or solver log is not accepted as proof by itself. The optimality certificate is independently checked by the verifier.

---

## Problem

Each project has:

- Project ID
- Base reward
- Financial cost
- Engineering-hours requirement
- Staffing requirement
- Energy consumption
- Risk value
- Prerequisite projects

If project `B` requires project `A`, selecting `B` also requires selecting `A`.

Dependencies can form long chains and can be shared by multiple projects. This means that selecting one project can require several additional projects and can change the overall resource usage of the portfolio.

The portfolio must satisfy five resource limits:

```text
Financial cost       <= Financial budget
Engineering hours   <= Engineering limit
Staffing             <= Staffing limit
Energy               <= Energy limit
Risk                 <= Risk limit
