import math
import xml.etree.ElementTree as ET
import numpy as np
from scipy.stats import t
from testing.testInstance import test_instances

# ===================== MEASUREMENTS ======================

correct_gates_sum = 0
incorrect_gates_sum = 0
results = []

for test in test_instances:
    print(test.name)

    gen_stats = ET.parse(test.gen_stats_out_file)
    real_stats = ET.parse(test.real_stats_file)

    # Get gate edges
    real_gate_edges = [xml_gate.get("edge") for xml_gate in real_stats.find("cityGates").findall("entrance")]
    gen_gate_edges = [xml_gate.get("edge") for xml_gate in gen_stats.find("cityGates").findall("entrance")]

    # Normalize gate edges (removing "-")
    real_gate_edges = [edge[1:] if edge[0] == "-" else edge for edge in real_gate_edges]
    gen_gate_edges = [edge[1:] if edge[0] == "-" else edge for edge in gen_gate_edges]

    # Count correct edges
    correct_gates = sum(int(gate in real_gate_edges) for gate in gen_gate_edges)
    incorrect_gates = len(gen_gate_edges) - correct_gates

    # Add results to sum
    correct_gates_sum += correct_gates
    incorrect_gates_sum += incorrect_gates
    results.append((len(real_gate_edges), len(gen_gate_edges), correct_gates, incorrect_gates,
                    correct_gates / len(gen_gate_edges)))

    # Print results
    print("  Generated / real gate count:", len(gen_gate_edges), "/", len(real_gate_edges))
    print("  Correct gates:", correct_gates)
    print("  Incorrect edges:", incorrect_gates)
    print("  % correct:", correct_gates / len(gen_gate_edges))

print("Summed results")
print("  Correct gates:", correct_gates_sum)
print("  Incorrect gates:", incorrect_gates_sum)

# ========================= T-TEST ======================

N = len(results)
mu = 0.5  # Null-hypothesis: less than 50% of gates are placed correctly

data = np.array(results).transpose()[4]  # Extract correct percentages
average = sum(data) / N
variance = sum((average - data) ** 2) / N
tstat = math.sqrt(N / variance) * (average - mu)
pvalue = 1 - t.cdf(tstat, N - 1)

print("  Average % correct:", average)
print("  Variance % correct:", variance)
print(f"  t-statistic (mu = {mu}): {tstat}")
print("  p-value:", pvalue)
