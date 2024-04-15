import pytest
import pyproj as pp
# from vyperdatum.transformer import Transformer
# from vyperdatum.db import DB


def test_NOAA_authority():
    """
    Check if NOAA is listed as authority in the proj.db.
    NOAA is not listed in the original proj.db.
    """
    print(pp.datadir.get_data_dir())
    assert "NOAA" in pp.database.get_authorities(), ("The authority 'NOAA' not found in proj.db. "
                                                     "Check if the latest database is used.")
