import xml.etree.ElementTree as ET

if __name__ == '__main__':
    stats = ET.parse("example.stat.xml")

    # Try to write to each street-element
    streets = stats.find("streets").findall("street")
    for street in streets:
        print(street.items(), street.attrib["population"])
        street.set("population", "42")

    brackets = stats.find("population").findall("bracket")
    dankPlaces = ET.SubElement(stats.getroot(), "dankPlaces")
    ET.SubElement(dankPlaces, "place", {"name": "Aalborg University"})
    ET.SubElement(dankPlaces, "place", {"name": "Elika's Pizza"})
    ET.SubElement(dankPlaces, "place", {"name": "Dice'n'Drinks"})
    stats.write("out/stats2.xml")