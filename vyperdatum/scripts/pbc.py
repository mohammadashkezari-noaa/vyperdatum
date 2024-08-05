import os
import pathlib
import glob
from vyperdatum.transformer import Transformer
from vyperdatum.utils.raster_utils import raster_metadata, raster_compress
from osgeo import gdal
import pyproj as pp


def transform(input_file, input_crs, out_vertical):
    warp_kwargs_vertical = {
                            "outputType": gdal.gdalconst.GDT_Float32,
                            "srcBands": [1],
                            "dstBands": [1],
                            "warpOptions": ["APPLY_VERTICAL_SHIFT=YES"],
                            "errorThreshold": 0,
                            }

    t1 = Transformer(crs_from=input_crs,
                     crs_to="EPSG:6319",
                     allow_ballpark=False
                     )
    out_file1 = pathlib.Path(input_file).with_stem("_01_" + pathlib.Path(input_file).stem)
    t1.transform_raster(input_file=input_file,
                        output_file=out_file1,
                        apply_vertical=False,
                        )

    t2 = Transformer(crs_from="EPSG:6319",
                     crs_to=f"EPSG:6318+{out_vertical}",
                     allow_ballpark=False
                     )
    out_file2 = pathlib.Path(input_file).with_stem("_02_" + pathlib.Path(input_file).stem)
    t2.transform_raster(input_file=out_file1,
                        output_file=out_file2,
                        apply_vertical=True,
                        warp_kwargs=warp_kwargs_vertical
                        )

    t3 = Transformer(crs_from=f"EPSG:6318+{out_vertical}",
                     crs_to=f"{input_crs}+{out_vertical}",
                     allow_ballpark=False
                     )
    p = pathlib.Path(input_file)
    xform_dir = os.path.join(r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\PBC\V\Manual", p.parent.name)
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
    files = glob.glob(r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\PBC\V\Original\**\*.tif", recursive=True)
    for i, input_file in enumerate(files):
        print(f"{i+1}/{len(files)}: {input_file}")
        if os.path.basename(input_file).startswith("MA"):
            transformed_file = transform(input_file, input_crs="EPSG:6348", out_vertical="NOAA:5320")
        elif os.path.basename(input_file).startswith("ma"):
            transformed_file = transform(input_file, input_crs="EPSG:26919", out_vertical="NOAA:5320")
        elif os.path.basename(input_file).startswith("ct") or os.path.basename(input_file).startswith("rh"):
            transformed_file = transform(input_file, input_crs="EPSG:26919", out_vertical="NOAA:5434")
