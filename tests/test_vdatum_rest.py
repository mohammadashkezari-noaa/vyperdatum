
import pytest
from vyperdatum.utils.raster_utils import raster_metadata
from vyperdatum.utils.vdatum_rest_utils import api_crs_aliases


@pytest.mark.parametrize("input_file, vdatum_h_crs, vdatum_v_crs", [
    (r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\NVD\VA_input.tif", "ITRF2014", "LMSL"),
    (r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\BlueTopo\BC25L26L\Modeling_BC25L26L_20230919.tiff", "NAD83_2011", "MLLW"),
    (r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\BlueTopo\BC25L26L\_03_6318_5703_Modeling_BC25L26L_20230919.tiff", "NAD83_2011", "NAVD88"),
    ])
def test_api_crs_aliases(input_file: str, vdatum_h_crs: str, vdatum_v_crs: str):
    meta = raster_metadata(input_file, verbose=False)
    h_crs, v_crs = api_crs_aliases(meta["wkt"])
    assert h_crs == vdatum_h_crs, "unexpected band counts"
