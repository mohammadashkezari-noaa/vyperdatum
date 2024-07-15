import os
import glob
import pathlib
from vyperdatum.transformer import Transformer
from vyperdatum.utils.raster_utils import raster_metadata, raster_compress
from osgeo import gdal
import pyproj as pp


def transform_NC(input_file):
    """
    3-Step transformation:
    EPSG:6347 >>> EPSG:6319
    EPSG:6319 >>> EPSG:6318+NOAA:5374
    EPSG:6318+NOAA:5374 >>> EPSG:6347+NOAA:5374
    """
    warp_kwargs_vertical = {
                            "outputType": gdal.gdalconst.GDT_Float32,
                            "srcBands": [1],
                            "dstBands": [1],
                            "warpOptions": ["APPLY_VERTICAL_SHIFT=YES"],
                            "errorThreshold": 0,
                            }

    t1 = Transformer(crs_from="EPSG:6347",
                     crs_to="EPSG:6319",
                     allow_ballpark=False
                     )
    out_file1 = pathlib.Path(input_file).with_stem("_01_" + pathlib.Path(input_file).stem)
    t1.transform_raster(input_file=input_file,
                        output_file=out_file1,
                        apply_vertical=False,
                        )

    t2 = Transformer(crs_from="EPSG:6319",
                     crs_to="EPSG:6318+NOAA:5374",
                     allow_ballpark=False
                     )
    out_file2 = pathlib.Path(input_file).with_stem("_02_" + pathlib.Path(input_file).stem)
    t2.transform_raster(input_file=out_file1,
                        output_file=out_file2,
                        apply_vertical=True,
                        warp_kwargs=warp_kwargs_vertical
                        )

    t3 = Transformer(crs_from="EPSG:6318+NOAA:5374",
                     crs_to="EPSG:6347+NOAA:5374",
                     allow_ballpark=False
                     )
    # out_file3 = pathlib.Path(input_file).with_stem("_03_" + pathlib.Path(input_file).stem)
    p = pathlib.Path(input_file)
    xform_dir = os.path.join(r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\NC\Manual", p.parent.name)
    os.makedirs(xform_dir, exist_ok=True)
    out_file3 = os.path.join(xform_dir, p.name)
    t3.transform_raster(input_file=out_file2,
                        output_file=out_file3,
                        apply_vertical=False,
                        )

    os.remove(out_file1)
    os.remove(out_file2)
    return out_file3


if __name__ == "__main__":
    files = glob.glob(r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\NC\**\VA*.tif", recursive=True)
    print(files)
    print(len(files))
    for i, input_file in enumerate(files):
        print(f"{i+1}/{len(files)}: {input_file}")
        if os.path.basename(input_file).startswith("NC"):
            transformed_file = transform_NC(input_file)
        elif os.path.basename(input_file).startswith("VA"):
            transformed_file = transform_VA(input_file)
        transformed_meta = raster_metadata(transformed_file, verbose=True)

    # fully uncovered
    # input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\NC\NC1903-TB-C_BLK-07_US4NC1EI_ellipsoidal_dem.tif"
    
    # # mostly covered
    # input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\NC\NC1901-TB-C_BLK-04_US4NC1DI_ellipsoidal_dem.tif"
