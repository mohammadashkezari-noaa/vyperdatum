import pathlib
from vyperdatum.transformer import Transformer
from vyperdatum.utils.raster_utils import raster_metadata


def transform(input_file):
    warp_kwargs_vertical = {
                            "srcBands": [1],
                            "dstBands": [1],
                            "warpOptions": ["APPLY_VERTICAL_SHIFT=YES"],
                            "errorThreshold": 0,
                            }
    t1 = Transformer(crs_from="EPSG:9000+NOAA:5197",
                     crs_to="EPSG:9000+NOAA:5200",
                     allow_ballpark=False
                     )
    out_file = pathlib.Path(input_file).with_stem("_transformed_" + pathlib.Path(input_file).stem)
    t1.transform_raster(input_file=input_file,
                        output_file=out_file,
                        apply_vertical=True,
                        warp_kwargs=warp_kwargs_vertical
                        )
    return out_file


if __name__ == "__main__":
    input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\NVD\VA_input.tif"
    transformed_file = transform(input_file)
    transformed_meta = raster_metadata(transformed_file, verbose=True)
