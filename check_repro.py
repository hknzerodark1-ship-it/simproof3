#!/usr/bin/env python3
"""Reproducibility checker for simulation pipelines - ROS2, CUDA, ML"""

import json
import sys
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Tuple

def load_trace(path: str) -> Dict:
    """Load trace JSON file"""
    with open(path, 'r') as f:
        return json.load(f)

def compare_event_orders(trace_a: Dict, trace_b: Dict) -> Tuple[bool, float, str]:
    """Compare event sequences for ordering differences"""
    events_a = trace_a.get('events', [])
    events_b = trace_b.get('events', [])
    
    if len(events_a) != len(events_b):
        return True, 0.95, f"Event count mismatch: {len(events_a)} vs {len(events_b)}"
    
    # Extract node sequences
    nodes_a = [e.get('node', 'unknown') for e in events_a]
    nodes_b = [e.get('node', 'unknown') for e in events_b]
    
    if nodes_a != nodes_b:
        diff_idx = next(i for i, (a, b) in enumerate(zip(nodes_a, nodes_b)) if a != b)
        return True, 0.91, f"Node sequence mismatch at position {diff_idx}: ...{nodes_a[diff_idx-1:diff_idx+2]} vs {nodes_b[diff_idx-1:diff_idx+2]}"
    
    return False, 0.0, ""

def compare_rng_states(trace_a: Dict, trace_b: Dict) -> Tuple[bool, float, str]:
    """Compare RNG seed states"""
    rng_a = trace_a.get('rng_states', {})
    rng_b = trace_b.get('rng_states', {})
    
    if not rng_a.get('python_seed') or not rng_b.get('python_seed'):
        return True, 0.87, "Missing Python seed in one or both runs"
    
    if rng_a.get('python_seed') != rng_b.get('python_seed'):
        return True, 0.82, f"Seed mismatch: {rng_a.get('python_seed')} vs {rng_b.get('python_seed')}"
    
    if rng_a.get('cuda_deterministic') != rng_b.get('cuda_deterministic'):
        return True, 0.71, f"CUDA deterministic flag mismatch: {rng_a.get('cuda_deterministic')} vs {rng_b.get('cuda_deterministic')}"
    
    return False, 0.0, ""

def compare_outputs(trace_a: Dict, trace_b: Dict) -> Tuple[bool, float, str]:
    """Compare final outputs for numeric drift"""
    outputs_a = trace_a.get('outputs', {})
    outputs_b = trace_b.get('outputs', {})
    
    common_keys = set(outputs_a.keys()) & set(outputs_b.keys())
    if not common_keys:
        return False, 0.0, ""
    
    max_diff = 0.0
    diff_key = None
    for key in common_keys:
        val_a = outputs_a.get(key, 0)
        val_b = outputs_b.get(key, 0)
        if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
            diff = abs(val_a - val_b)
            if val_a != 0:
                diff = diff / abs(val_a)
            if diff > max_diff:
                max_diff = diff
                diff_key = key
    
    if max_diff > 0.0001:
        return True, min(0.63 + max_diff, 0.95), f"Numeric divergence in '{diff_key}': {max_diff:.4f} relative difference"
    
    return False, 0.0, ""

def hash_trace(trace: Dict) -> str:
    """Generate deterministic hash of trace content"""
    # Remove timestamps for comparison
    trace_copy = {k: v for k, v in trace.items() if k not in ['timestamp', 'run_id']}
    return hashlib.sha256(json.dumps(trace_copy, sort_keys=True).encode()).hexdigest()

def check_reproducibility(trace_a_path: str, trace_b_path: str) -> int:
    """Main reproducibility check"""
    print("🔍 SIMPROOF — Deterministic Reproducibility Debugging")
    print("=" * 60)
    print(f"   Trace A: {trace_a_path}")
    print(f"   Trace B: {trace_b_path}")
    print()
    
    try:
        trace_a = load_trace(trace_a_path)
        trace_b = load_trace(trace_b_path)
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ JSON parse error: {e}")
        return 1
    
    # Quick hash comparison
    if hash_trace(trace_a) == hash_trace(trace_b):
        print("✅ RESULT: DETERMINISTIC")
        print("   Both traces are identical — simulation is reproducible")
        return 0
    
    print("❌ RESULT: NON_DETERMINISTIC")
    print("   Traces differ — identifying root causes...")
    print()
    
    causes = []
    
    # Check event ordering (ROS2)
    has_diff, conf, evidence = compare_event_orders(trace_a, trace_b)
    if has_diff:
        causes.append({
            "cause": "ROS2 callback ordering nondeterminism",
            "confidence": conf,
            "evidence": evidence,
            "fix": "Switch to SingleThreadedExecutor or enforce deterministic QoS"
        })
    
    # Check RNG seeds
    has_diff, conf, evidence = compare_rng_states(trace_a, trace_b)
    if has_diff:
        causes.append({
            "cause": "RNG seed not propagated",
            "confidence": conf,
            "evidence": evidence,
            "fix": "Set global seed at simulation root and propagate to all plugins"
        })
    
    # Check numeric outputs (GPU drift)
    has_diff, conf, evidence = compare_outputs(trace_a, trace_b)
    if has_diff:
        causes.append({
            "cause": "GPU kernel nondeterminism / floating point drift",
            "confidence": conf,
            "evidence": evidence,
            "fix": "Disable nondeterministic CUDA kernels or use deterministic flags"
        })
    
    # Fallback
    if not causes:
        causes.append({
            "cause": "Unknown nondeterminism source",
            "confidence": 0.50,
            "evidence": "Traces differ but no specific pattern matched",
            "fix": "Enable verbose tracing and compare step-by-step"
        })
    
    # Print ranked causes
    print("Top Causes:\n")
    for i, cause in enumerate(causes[:3], 1):
        print(f"[{i}] {cause['cause']}")
        print(f"    confidence: {cause['confidence']:.2f}")
        print(f"    evidence: {cause['evidence']}")
        print(f"    fix: {cause['fix']}")
        print()
    
    print("=" * 60)
    return 1

def scan_directory(path: str) -> int:
    """Scan directory for trace files and check latest two"""
    path = Path(path)
    trace_files = list(path.glob("*trace*.json")) + list(path.glob("*.trace.json"))
    
    if not trace_files:
        print("🔍 SIMPROOF — Directory Scan")
        print("=" * 60)
        print(f"   Path: {path}")
        print("\n⚠️  No trace files found")
        print("\n💡 To create test traces:")
        print("   python -c \"import json; json.dump({'events': [], 'outputs': {'value': 1}}, open('trace1.json', 'w'))\"")
        print("   python -c \"import json; json.dump({'events': [], 'outputs': {'value': 1}}, open('trace2.json', 'w'))\"")
        return 0
    
    if len(trace_files) == 1:
        print("🔍 SIMPROOF — Directory Scan")
        print("=" * 60)
        print(f"   Found 1 trace file: {trace_files[0].name}")
        print("\n⚠️  Need at least 2 traces to compare")
        print("   Run another simulation to generate second trace")
        return 0
    
    # Compare two most recent
    trace_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    print(f"Comparing {trace_files[0].name} vs {trace_files[1].name}")
    return check_reproducibility(str(trace_files[0]), str(trace_files[1]))

if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(check_reproducibility(sys.argv[1], sys.argv[2]))
    elif len(sys.argv) == 2 and sys.argv[1] == "check":
        sys.exit(scan_directory("."))
    else:
        print("SIMPROOF — Deterministic Reproducibility Debugging")
        print()
        print("Usage:")
        print("  python check_repro.py traceA.json traceB.json  # Compare two traces")
        print("  python check_repro.py check                    # Scan current directory")
        print()
        print("Exit codes:")
        print("  0 = Deterministic (reproducible)")
        print("  1 = Non-deterministic (not reproducible)")
        sys.exit(1)
