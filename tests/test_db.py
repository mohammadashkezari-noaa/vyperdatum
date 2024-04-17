import pyproj as pp


def test_NOAA_authority():
    """
    Check if NOAA is listed as authority in the proj.db.
    NOAA is not listed in the original proj.db.
    """
    assert "NOAA" in pp.database.get_authorities(), ("The authority 'NOAA' not found in proj.db. "
                                                     "Check if the latest database is used.")
