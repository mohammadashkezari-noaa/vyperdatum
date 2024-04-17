import pytest
from vyperdatum.transformer import Transformer


def test_6349_to_6319():
    """
    Verify the a point on NAD83_2011_NAVD88 (EPSG:6349) is transformed
    correctly to NAD83_2011_3D (EPSG:6319).

    If network is off then a noop is used for the transform and NAVD88 to
    NAD83_2011_3D returns 0.0 leading to the test failure.
    """

    coords_lat_lon = (39, -76.5, 0)
    x, y, z = Transformer(crs_from=6349, crs_to=6319).transform_points(*coords_lat_lon)
    assert pytest.approx(x, abs=.01) == coords_lat_lon[0], "x coordinate should remain unchanged."
    assert pytest.approx(y, abs=.01) == coords_lat_lon[1], "y coordinate should remain unchanged."
    assert pytest.approx(z, abs=.01) == -33.29, "incorrect z coordinate transformation."
