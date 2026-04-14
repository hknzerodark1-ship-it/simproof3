#!/usr/bin/env python3
"""Demo simulation for SIMPROOF"""

import random
import json

def run_simulation(seed=None, output_path=None):
    if seed is not None:
        random.seed(seed)
    
    results = [random.random() for _ in range(10)]
    final_value = sum(results)
    
    trace = {
        "version": "1.0",
        "run_id": f"run_{seed}" if seed else "run_no_seed",
        "rng": {"seed": seed, "deterministic": seed is not None},
        "events": [{"timestamp": i * 0.1, "name": "random.random"} for i in range(10)],
        "outputs": {"mean": final_value / 10}
    }
    
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(trace, f, indent=2)
        print(f"📊 Trace saved: {output_path}")
    
    return final_value

if __name__ == "__main__":
    run_simulation(seed=42, output_path="trace_seed_42.json")
    run_simulation(seed=None, output_path="trace_no_seed.json")
    print("\n✅ Demo traces created")
    print("Run: simproof compare trace_seed_42.json trace_no_seed.json")
