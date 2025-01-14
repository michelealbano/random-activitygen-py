import os
import pathlib
import sys
from typing import List

import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial.distance import cdist
from scipy.optimize import linear_sum_assignment
import xml.etree.ElementTree as ET
import seaborn as sns
import csv

from scipy.stats import ttest_1samp

from testing.testInstance import TestInstance, test_instances
from utility import position_on_edge

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib


def calc_school_divergence(test: TestInstance, plot: bool) -> List[float]:
    """
    Calculate the divergence between generated and real schools by solving the assignment problem on them
     and plot these schools and assignments on the network if enabled.
    :param test: the given TestInstance to test
    :param plot: whether to plot the city, schools, and assignments
    :return: the divergence for each assigned school
    """
    net: sumolib.net.Net = sumolib.net.readNet(test.net_file)

    # Get mean school coordinates for real and generated statistics
    gen_coords = np.array(
        [position_on_edge(net.getEdge((xml_school.get("edge"))), float(xml_school.get("pos"))) for xml_school in
         ET.parse(test.gen_stats_out_file).find("schools").findall("school")])

    real_coords = np.array(
        [position_on_edge(net.getEdge((xml_school.get("edge"))), float(xml_school.get("pos"))) for xml_school in
         ET.parse(test.real_stats_file).find("schools").findall("school")])

    # Get euclidean distance between all points in both sets as a cost matrix.
    # Note that the ordering is seemingly important for linear_sum_assignment to work.
    #  Not ordering causes points in the larger set, larger than the max size of the smaller set to be ignored.
    if len(real_coords) > len(gen_coords):
        dist = cdist(gen_coords, real_coords)
    else:
        dist = cdist(real_coords, gen_coords)

    # Solve the assignment problem
    _, assignment = linear_sum_assignment(dist)

    if plot:
        plot_school_assignment(net, test.name, gen_coords, real_coords, assignment)

    # return list of assigned schools divergence
    return [dist[i, assignment[i]] for i in range(0, min(len(gen_coords), len(real_coords)))]


def plot_school_assignment(net: sumolib.net.Net, test_name: str, gen_coords: np.ndarray, real_coords: np.ndarray,
                           assignment: np.ndarray) -> None:
    # Draw streets
    [plt.plot([pos1[0], pos2[0]], [pos1[1], pos2[1]], "grey") for pos1, pos2 in
     [edge.getShape()[i:i + 2] for edge in net.getEdges() for i in range(0, int(len(edge.getShape()) - 1))]]

    # Plot generated points as blue circles, and real ones as red squares
    plt.plot(gen_coords[:, 0], gen_coords[:, 1], 'bo', markersize=10, label="Gen")
    plt.plot(real_coords[:, 0], real_coords[:, 1], 'rs', markersize=7, label="Real")

    # Plot lines between assigned points. Note that this is also ordered, hence the swap
    if len(real_coords) <= len(gen_coords):
        real_coords, gen_coords = gen_coords, real_coords
    for p in range(0, min(len(gen_coords), len(real_coords))):
        plt.plot([gen_coords[p, 0], real_coords[assignment[p], 0]],
                 [gen_coords[p, 1], real_coords[assignment[p], 1]], 'k', label="Assign" if p == 0 else "")

    plt.legend(loc='lower left')  # Set to lower left for continuity in paper
    plt.axis('off')
    # plt.title(f"School placement test for {test_name}")  # Title disabled for paper
    plt.show()


def test_total_placement(results: list, max_distance: float) -> bool:
    """
    Tests whether each result is within some max distance
    :param results: a list of results/divergences
    :param max_distance: the max distance to test for
    :return: bool whether all are placed within max distance
    """
    for result in results:
        if result > max_distance:
            return False
    return True


def t_test(test: TestInstance, divs: list, bound: float, times: int = 1) -> None:
    """
    T-tests on a given TestInstance and prints results.
    :param test: TestInstance to test on
    :param divs: list of divergences
    :param bound: the max distance to test for
    :param times: number of runs the test was run for
    :return: None
    """
    print(f"Executing school placement one-sided t-test on {times} runs of {test.name}")

    # Flatten list of divergences, only when divs contains lists
    if any(isinstance(element, list) for element in divs):
        divs = [dist for div in divs for dist in div]

    print(f"\tAll schools placed closer than bound: {test_total_placement(divs, bound)}")
    print(f"\tMean divergence: {np.mean(divs):.2f} meters")
    if len(divs) < 2:
        print("\t[WARN] Cannot make a t-test on a single divergence")
        if np.mean(divs) <= bound:
            print(f"\tHowever, the divergence ({np.mean(divs):.2f} meters) is less or equal than {bound}")
        else:
            print(f"\tHowever, the divergence ({np.mean(divs):.2f} meters) is greater than {bound}", )
        return

    t_stat, p_val = ttest_1samp(divs, bound)
    # To obtain a one-sided p-value, divide by 2 as the probability density function is symmetric
    p_val = p_val / 2

    print(f"\tT-test with bound {bound} meters. T-stat: {t_stat}, p-value: {p_val}")
    if t_stat <= 0:
        if p_val <= 0.05:
            print(f"\tSince t-stat is zero or negative, and p-value is of statistical significance (p <= 0.05), "
                  f"the null-hypothesis can be rejected.")
        else:
            print("\tSince p-value is not of statistical significance, the null-hypothesis cannot be rejected.")
    else:
        if p_val <= 0.05:
            print("\tThe t-stat is not zero or negative, and p-value is of statistical significance (p <= 0.05),"
                  "the null-hypothesis can be rejected.")
        else:
            print("\tSince p-value is not of statistical significance, the null-hypothesis cannot be rejected.")


def run_multiple_test(test: TestInstance, bound: float, times: int = 1) -> None:
    """
    Runs multiple tests on a given instance by sequentially calling the tool and calculating divergences.
     These are collected and finally t-tested against the bound.
    :param test: TestInstance to test on
    :param bound: the maximum distance to test against
    :param times: how many times to run a single TestInstance
    :return: None
    """
    # Get number of real schools
    num_real_schools = len(ET.parse(test.real_stats_file).find("schools").findall("school"))

    divs = []
    for n in range(0, times):
        # Run tool
        test.run_tool(num_real_schools)

        # Calculate and collect derivations
        divs += [calc_school_divergence(test, True)]

    # test within bound on derivations
    t_test(test, divs, bound, times)


def calc_divergence(test: TestInstance) -> List[float]:
    """
    Calculate a single run of divergences on a newly generated scenario and return them
    :param test: TestInstance to test on
    :return: list of divergences
    """
    # Run tool with number of real schools
    test.run_tool(len(ET.parse(test.real_stats_file).find("schools").findall("school")))
    return calc_school_divergence(test, False)


def write_divergences(test: TestInstance, dir: str) -> None:
    """
    Writes or appends divergences to a file under dir named after the test's name.
    :param test: TestInstance to test on
    :param dir: directory to place files in
    :return: None
    """
    path = f"{dir}/{test.name}-divergences.csv"
    if not os.path.exists(dir):
        os.mkdir(dir)
    if not os.path.exists(path):
        pathlib.Path(path).touch()

    with open(path, "r", newline='') as f:
        if len(f.readlines()) == 0:
            f.close()
            with open(path, "w", newline='') as f:
                writer = csv.writer(f, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(calc_divergence(test))
                f.close()
        else:
            f.close()
            with open(path, "a+", newline='') as f:
                writer = csv.writer(f, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(calc_divergence(test))
                f.close()


def read_divergences(test: TestInstance, dir: str) -> np.ndarray:
    """
    Reads divergences from file
    :param test: TestInstance to read list for
    :param dir: containing directory of files
    :return: list of divergences
    """
    with open(f"{dir}/{test.name}-divergences.csv", "r+", newline='') as f:
        return np.array(list(csv.reader(f, delimiter=',', quotechar='|')), np.float32)


if __name__ == '__main__':
    # sns.set()  # Use seaborn bindings for matplotlib, good for histograms, etc.
    bound = 2000
    print(f"Testing school placement on following cities: {', '.join([test.name for test in test_instances])}")
    print(f"Null hypothesis: Generated schools are placed further than {bound} meters away from real schools")
    print(f"Alt. hypothesis: Generated schools are placed exactly or closer than {bound} meters away from real schools")
    # [t_test(test, calc_school_divergence(test, True), bound, 1) for test in test_instances[4:]]  # One run per test

    # [run_multiple_test(test, bound, 2) for test in test_instances]  # Multiple runs per test

    # [write_divergences(test, "divergences") for test in test_instances]  # Write one run of divergences to file
    # [t_test(test, read_divergences(test, "divergences"), bound, 1) for test in test_instances]  # Run t-test on all

    # sns.distplot(read_divergences(test_instances[0], "divergences"))  # Plot a pretty distribution histogram from file
    # plt.show()
