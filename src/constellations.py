from math import radians, sin, cos

# Minimal clean constellation dataset
# Only a few bright stars for now (can expand later)

CONSTELLATIONS = {
    "Orion": [
        # (Star Name, RA°, Dec°)
        ("Betelgeuse", 88.7929, 7.4071),
        ("Bellatrix", 81.2828, 6.3497),
        ("Alnitak", 85.1897, -1.9426),
        ("Alnilam", 84.0534, -1.2019),
        ("Mintaka", 83.0017, -0.2991),
        ("Saiph", 86.9391, -9.6696),
        ("Rigel", 78.6345, -8.2016),
    ],

    "Ursa Major": [
        ("Dubhe", 165.460, 61.751),
        ("Merak", 165.932, 56.382),
        ("Phecda", 178.457, 53.694),
        ("Megrez", 183.856, 57.032),
        ("Alioth", 193.507, 55.959),
        ("Mizar", 200.981, 54.925),
        ("Alkaid", 206.885, 49.313),
    ],

    "Cassiopeia": [
        ("Schedar", 10.126, 56.537),
        ("Caph", 2.293, 59.149),
        ("Tsih", 14.177, 60.716),
        ("Ruchbah", 10.127, 60.235),
        ("Segin", 28.598, 63.670),
    ],
}
