import os
import pathlib
from osgeo import gdal, osr
import numpy as np
import pyproj as pp
import pytest
from vyperdatum.transformer import Transformer
from vyperdatum.npz import NPZ


def raster_wkt(raster_file: str):
    wkt = None
    if pathlib.Path(raster_file).suffix.lower() == ".npz":
        wkt = NPZ(raster_file).wkt()
    else:
        ds = gdal.Open(raster_file)
        srs = osr.SpatialReference(wkt=ds.GetProjection())
        wkt = srs.ExportToWkt()
        ds = None
    return wkt


@pytest.mark.parametrize("input_file, already_transformed_file", [
    (r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\Modeling_BC25L26L_20230919.tiff",
     r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\BlueTopo_BC25L26L_20230919.tiff"),

    (r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\W00405_MB_1m_MLLW_1of4.bag",
     r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\W00405_MB_1m_MLLW_1of4_transformed.bruty.npz"),

    (r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\2018_NCMP_MA_19TCF2495_BareEarth_1mGrid.tif",
     r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\2018_NCMP_MA_19TCF2495_BareEarth_1mGrid_transformed.bruty.bruty.npz"),
                                                     ])
def test_transform_raster(input_file: str, already_transformed_file: str):
    generated_file = str(pathlib.Path(input_file).with_stem("_generated_" + pathlib.Path(input_file).stem))
    if os.path.isfile(generated_file):
        os.remove(generated_file)
    T = Transformer(crs_from=raster_wkt(input_file),
                    crs_to=raster_wkt(already_transformed_file)
                    )
    T.transform_raster(input_file=input_file, output_file=generated_file)
    if (pathlib.Path(generated_file).suffix in T.gdal_extensions()
        and
        pathlib.Path(already_transformed_file).suffix in T.gdal_extensions()
        ):
        gen_ds = gdal.Open(generated_file)
        target_ds = gdal.Open(already_transformed_file)
        gen_band = np.nan_to_num(gen_ds.GetRasterBand(1).ReadAsArray())
        target_band = np.nan_to_num(target_ds.GetRasterBand(1).ReadAsArray())
        assert gen_ds.RasterCount == target_ds.RasterCount, "unexpected band counts"
        assert pytest.approx(gen_band.min(), 0.001) == target_band.min(), f"inconsistent min band value (gen_min: {gen_band.min()} vs target_min: {target_band.min()})"
        assert pytest.approx(gen_band.max(), 0.001) == target_band.max(), f"inconsistent max band value (gen_max: {gen_band.max()} vs target_max: {target_band.max()})"
        gen_band.flags.writeable = False
        target_band.flags.writeable = False
        assert hash(gen_band) == hash(target_band), f"hash check failed ({hash(gen_band)} vs {hash(target_band)})"
        # assert gen_ds.GetRasterBand(1).Checksum() == target_ds.GetRasterBand(1).Checksum(), f"checksum failed ({gen_ds.GetRasterBand(1).Checksum()} vs {target_ds.GetRasterBand(1).Checksum()})"
        # assert pp.CRS(raster_wkt(already_transformed_file)).equals(pp.CRS(raster_wkt(generated_file))), "inconsistent crs."
        gen_ds, target_ds = None, None
        gen_band, target_band = None, None
