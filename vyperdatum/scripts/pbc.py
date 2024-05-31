import pathlib
sys.path.append("..")
from transformer import Transformer
from utils.raster_utils import raster_metadata


def transform(input_file):
    # NAD83(2011) / UTM 19N >>>>  NAD83(2011) / UTM 19N + MLLW height
    t1 = Transformer(crs_from="EPSG:6348",
                     crs_to="EPSG:6348+NOAA:5320",
                     allow_ballpark=False
                     )
    out_file1 = pathlib.Path(input_file).with_stem("_transformed_" + pathlib.Path(input_file).stem)
    t1.transform_raster(input_file=input_file,
                        output_file=out_file1,
                        apply_vertical=True
                        )
    return


if __name__ == "__main__":
    input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\PBC\MA2204-TB-N_TPU_3band_mosaic_tpu.tif"
    print(raster_metadata(input_file, verbose=True))
    transform(input_file)
