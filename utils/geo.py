import math

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance in kilometers between two points using the Haversine formula.
    """
    R = 6371  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi/2)**2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


def sqlite_distance_expr(user_lat, user_lon):
    """
    Returns a SQLite SQL snippet to compute distance_km dynamically in a query.
    """
    return f"""(
        6371 * acos(
            cos(radians({user_lat})) * cos(radians(lat)) *
            cos(radians(lon) - radians({user_lon})) +
            sin(radians({user_lat})) * sin(radians(lat))
        )
    ) AS distance_km"""


