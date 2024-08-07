import os
import pathlib
from vyperdatum.transformer import Transformer
from vyperdatum.utils.raster_utils import raster_metadata, raster_compress
from osgeo import gdal
import pyproj as pp


def get_tiff_files(parent_dir: str, extention: str) -> list:
    tiff_files = []
    for (dirpath, dirnames, filenames) in os.walk(parent_dir):
        for filename in filenames:
            if filename.endswith(extention):
                tiff_files.append(os.sep.join([dirpath, filename]))
    return tiff_files


def transform_FL(input_file):
    """
    3-Step transformation:
    EPSG:6346 >>> EPSG:6319
    EPSG:6319 >>> EPSG:6318+NOAA:5224
    EPSG:6318+NOAA:5224 >>> EPSG:6346+NOAA:5224
    """
    warp_kwargs_vertical = {
                            "outputType": gdal.gdalconst.GDT_Float32,
                            "srcBands": [1],
                            "dstBands": [1],
                            "warpOptions": ["APPLY_VERTICAL_SHIFT=YES"],
                            "errorThreshold": 0,
                            }

    t1 = Transformer(crs_from="EPSG:6346",
                     crs_to="EPSG:6319",
                     allow_ballpark=False
                     )
    out_file1 = pathlib.Path(input_file).with_stem("_01_" + pathlib.Path(input_file).stem)
    t1.transform_raster(input_file=input_file,
                        output_file=out_file1,
                        apply_vertical=False,
                        )

    t2 = Transformer(crs_from="EPSG:6319",
                     crs_to="EPSG:6318+NOAA:5224",
                     allow_ballpark=False
                     )
    out_file2 = pathlib.Path(input_file).with_stem("_02_" + pathlib.Path(input_file).stem)
    t2.transform_raster(input_file=out_file1,
                        output_file=out_file2,
                        apply_vertical=True,
                        warp_kwargs=warp_kwargs_vertical
                        )

    t3 = Transformer(crs_from="EPSG:6318+NOAA:5224",
                     crs_to="EPSG:6346+NOAA:5224",
                     allow_ballpark=False
                     )
    # p = pathlib.Path(input_file)
    # xform_dir = os.path.join(r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\NC\Manual", p.parent.name)
    # os.makedirs(xform_dir, exist_ok=True)
    # out_file3 = os.path.join(xform_dir, p.name)

    out_file3 = str(input_file).replace("Original", "Manual")
    os.makedirs(os.path.split(out_file3)[0], exist_ok=True)
    t3.transform_raster(input_file=out_file2,
                        output_file=out_file3,
                        apply_vertical=False,
                        )

    os.remove(out_file1)
    os.remove(out_file2)
    return out_file3


if __name__ == "__main__":
    parent_dir = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\PBB\Original"
    files = get_tiff_files(parent_dir, extention=".tif")
    for i, input_file in enumerate(files[:1]):
        print(f"{i+1}/{len(files)}: {input_file}")
        raster_metadata(input_file, verbose=True)
        if os.path.basename(input_file).startswith("FL"):
            transformed_file = transform_FL(input_file)
        elif os.path.basename(input_file).startswith("SC"):
            pass
            # transformed_file = transform_SC(input_file)
        raster_metadata(transformed_file, verbose=True)
        print(f'\n{"*"*50} {i+1}/{len(files)} Completed {"*"*50}\n')
