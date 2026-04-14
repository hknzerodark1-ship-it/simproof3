# SIMPROOF — Deterministic Reproducibility Debugging

**"Why did my simulation change when nothing changed?"**

SIMPROOF helps identify **likely sources of nondeterminism and reproducibility drift** in simulation pipelines, ROS2 systems, and ML training runs.

## Scope

SIMPROOF currently detects:

- ✅ RNG seed inconsistencies (Python / C++-level traces)
- ✅ Common ROS2 execution nondeterminism patterns
- ✅ Basic numeric drift indicative of GPU/physics instability

**Does NOT yet guarantee:**
- ❌ Full physical determinism analysis
- ❌ Deep CUDA kernel inspection
- ❌ Complete simulator internals coverage (Gazebo / Isaac Sim plugins)

## How It Works

SIMPROOF analyzes **execution traces**. To get full results, you must instrument your pipeline:

```python
from simproof import trace_simulation

@trace_simulation("my_run.json")
def my_simulation(seed=42):
    # your simulation code here
    return result
