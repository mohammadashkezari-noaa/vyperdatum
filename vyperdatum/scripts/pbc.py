import pathlib
from vyperdatum.transformer import Transformer
from vyperdatum.utils.raster_utils import raster_metadata, raster_compress
from osgeo import gdal
import pyproj as pp


def transform(input_file):
    """
    3-Step transformation:
    EPSG:6348 >>> EPSG:6319
    EPSG:6319 >>> EPSG:6318+NOAA:5320
    EPSG:6318+NOAA:5320 >>> EPSG:6348+NOAA:5320
    """
    warp_kwargs_vertical = {
                            "outputType": gdal.gdalconst.GDT_Float32,
                            "srcBands": [1],
                            "dstBands": [1],
                            "warpOptions": ["APPLY_VERTICAL_SHIFT=YES"],
                            "errorThreshold": 0,
                            }

    t1 = Transformer(crs_from="EPSG:6348",
                     crs_to="EPSG:6319",
                     allow_ballpark=False
                     )
    out_file1 = pathlib.Path(input_file).with_stem("_01_" + pathlib.Path(input_file).stem)
    t1.transform_raster(input_file=input_file,
                        output_file=out_file1,
                        apply_vertical=False,
                        )

    t2 = Transformer(crs_from="EPSG:6319",
                     crs_to="EPSG:6318+NOAA:5320",
                     allow_ballpark=False
                     )
    out_file2 = pathlib.Path(input_file).with_stem("_02_" + pathlib.Path(input_file).stem)
    t2.transform_raster(input_file=out_file1,
                        output_file=out_file2,
                        apply_vertical=True,
                        warp_kwargs=warp_kwargs_vertical
                        )

    t3 = Transformer(crs_from="EPSG:6318+NOAA:5320",
                     crs_to="EPSG:6348+NOAA:5320",
                     allow_ballpark=False
                     )
    out_file3 = pathlib.Path(input_file).with_stem("_03_" + pathlib.Path(input_file).stem)
    t3.transform_raster(input_file=out_file2,
                        output_file=out_file3,
                        apply_vertical=False,
                        )
    return out_file3




if __name__ == "__main__":
    input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\PBC\clipped_MA2204-TB-N_TPU_3band_mosaic_tpu.tif"
    compressed_input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\PBC\compressed_clipped_MA2204-TB-N_TPU_3band_mosaic_tpu.tif"
    input_meta = raster_metadata(input_file, verbose=True)
    raster_compress(input_file, compressed_input_file,
                    format=input_meta["driver"], compression="DEFLATE")

    transformed_file = transform(compressed_input_file)
    transformed_meta = raster_metadata(transformed_file, verbose=True)
