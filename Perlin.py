import decimal
import os
import sys
import xml.etree.ElementTree as ET
from xml.etree import ElementTree

import numpy as np

import noise

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib


def drange(x, y, jump):
    while x < y:
        yield float(x)
        x += decimal.Decimal(jump)


def test_perlin_noise():
    # Print 2d simplex noise in from x, y in 0..1 with step 0.1
    for x in drange(0, 1.01, 0.1):
        for y in drange(0, 1.01, 0.1):
            print(f"[{x:.2},{y:.2}] {noise.snoise2(x, y)}")


def get_shape_of_edge_name(net: sumolib.net.Net, edge: str) -> list:
    """
    Return the shape of an edge in coordinate form; [(x_1,y_1), (x_2,y_2), ... , (x_n,y_n)].
    :param net: the SUMO network
    :param edge: the edge ID
    :return: a tuple or list of tuples that define the shape of the edge
    """
    return net.getEdge(edge).getShape()


def get_edge_pair_centroid(coords: list) -> (float, float):
    """
    Centroid of rectangle (edge_pair) = (width/2, height/2)
    :param coords: [(x_1,y_1), (x_2,y_2), ... , (x_n,y_n)]
    :return: Centroid of given shape
    """

    x_avg = np.mean([pos[0] for pos in coords])
    y_avg = np.mean([pos[1] for pos in coords])
    return x_avg, y_avg


def scale_noise(noise: float) -> float:
    """
    The 'noise' lib returns a value in the range of [-1:1]. The noise value is scaled to the range of [0:1].
    :param noise: a float [-1:1]
    :return: the noise value scaled to [0:1]
    """
    return (noise + 1) / 2


def get_perlin_noise(x, y) -> float:
    """
    TODO: Find sane offset to combat zero-value at (0, 0)
    :param x:
    :param y:
    :return:
    """
    return scale_noise(noise.pnoise2(x, y))


def get_population_number(net: sumolib.net.Net, edge) -> float:
    """
    Returns a Perlin simplex noise at centre of given street
    :param net: the SUMO network
    :param edge: the edge ID
    :return: the scaled noise value as float in [0:1]
    """
    x, y = get_edge_pair_centroid(get_shape_of_edge_name(net, edge))
    return get_perlin_noise(x, y)


def get_edge_ids_in_network(net: sumolib.net.Net) -> list:
    """
    Returns a list of all edge IDs in the given SUMO network
    :param net: the SUMO network
    :return: a list of all edge IDs in the SUMO network
    """
    return list(map(lambda x: x.getID(), net.getEdges()))


def calculate_network_population(net: sumolib.net.Net, xml: ElementTree):
    """

    :param net: the SUMO network
    :param xml: the
    :return:
    """
    for edge in get_edge_ids_in_network(net):
        pop = get_population_number(net, edge)
        streets = xml.find("streets").findall("street")
        for street in streets:
            if street.attrib["edge"] == edge:
                street.set("population", str(pop))

    xml.write("out/stats2.xml")  # FIXME, testcode


def print_test():
    # Read networks
    grid_net = sumolib.net.readNet("in/example.net.xml")
    wavy_net = sumolib.net.readNet("in/example_wavy.net.xml")

    # Get shapes of edges. e01t11 is the bottom left vertical grid-street
    e01t11_shape = get_shape_of_edge_name(grid_net, "e11t12")
    gneE3_shape = get_shape_of_edge_name(wavy_net, "gneE3")

    print(e01t11_shape)
    print(gneE3_shape)

    # Get centroids of both edges
    print(get_edge_pair_centroid(e01t11_shape))
    print(get_edge_pair_centroid(gneE3_shape))

    # Get perlin weight for centroid of edge
    print(get_population_number(grid_net, "e11t12"))


if __name__ == '__main__':
    # Read in example SUMO network
    net = sumolib.net.readNet("in/example.net.xml")

    # Parse example statistics configuration
    stats = ET.parse("in/example.stat.xml")

    # Calculate and apply Perlin noise for all edges in network to population in statistics
    calculate_network_population(net, stats)
