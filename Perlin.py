import decimal
import os
import sys
import xml.etree.ElementTree as ET
import numpy as np

import noise

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

import sumolib


def drange(x, y, jump):
    while x < y:
        yield float(x)
        x += decimal.Decimal(jump)


def get_population_number(net, edge) -> float:
    """
    Returns a Perlin simplex noise at centre of given street
    TODO: Find sane offset to combat zero-value at (0, 0)
    :param net:
    :param edge:
    :return:
    """
    x, y = get_edge_pair_centroid(get_shape_of_edge_name(net, edge))
    return noise.snoise2(x, y)


def get_shape_of_edge_name(net, edge: str) -> (int, int):
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


def test_perlin_noise():
    # Print 2d simplex noise in from x, y in 0..1 with step 0.1
    for x in drange(0, 1.01, 0.1):
        for y in drange(0, 1.01, 0.1):
            print(f"[{x:.2},{y:.2}] {noise.snoise2(x, y)}")


def calculate_network_population(net, xml):
    for edge in get_edge_ids_in_network(net):
        pop = get_population_number(net, edge)
        streets = xml.find("streets").findall("street")
        for street in streets:
            if street.attrib["edge"] == edge:
                street.set("population", str(pop))

    xml.write("out/stats2.xml")  # FIXME, testcode


def get_edge_ids_in_network(net) -> list:
    return list(map(lambda x: x.getID(), net.getEdges()))


def print_test():
    # Read networks
    net = sumolib.net.readNet("example.net.xml")
    wavy_net = sumolib.net.readNet("example_wavy.net.xml")

    # Get shapes of edges. e01t11 is the bottom left vertical grid-street
    e01t11_shape = get_shape_of_edge_name(net, "e11t12")
    gneE3_shape = get_shape_of_edge_name(wavy_net, "gneE3")

    print(e01t11_shape)
    print(gneE3_shape)

    # Get centroids of both edges
    print(get_edge_pair_centroid(e01t11_shape))
    print(get_edge_pair_centroid(gneE3_shape))

    # Get perlin weight for centroid of edge
    print(get_population_number(net, "e11t12"))


if __name__ == '__main__':
    # print_test()
    net = sumolib.net.readNet("example.net.xml")
    stats = ET.parse("example.stat.xml")
    calculate_network_population(net, stats)
    # pprint(get_edge_ids_in_network(net))
