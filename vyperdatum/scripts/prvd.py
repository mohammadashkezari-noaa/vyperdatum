import os, sys, pathlib
import pyproj as pp
sys.path.append("..")
from transformer import Transformer
from utils.raster_utils import raster_metadata


def get_raster_crs(input_file: str, verbose: bool):
    wkt = raster_metadata(input_file)["wkt"]
    input_crs = pp.CRS(wkt)
    input_horizontal_crs = pp.CRS(input_crs.sub_crs_list[0])
    input_vertical_crs = pp.CRS(input_crs.sub_crs_list[1])    
    if verbose:
        print(f"{'-'*80}\nFile: {pathlib.Path(input_file).name}"
              f"\n\tInput CRS: {input_crs.name}"
              f"\n\tInput Horizontal Authority: {input_horizontal_crs.to_authority()}"
              f"\n\tInput Vertical Authority: {input_vertical_crs.to_authority()}"
              f"\n\tInput Vertical CRS: {input_vertical_crs}"
              f"\n{'-'*80}\n"
              )
    return input_crs, input_horizontal_crs, input_vertical_crs


def get_tiff_files(parent_dir: str) -> list:
    """
    Walk through the parent directory and return the absolute path of all .tiff files.
    """
    tiff_files = []
    for (dirpath, dirnames, filenames) in os.walk(parent_dir):
        for filename in filenames:
            if filename.endswith(".tiff"):
                tiff_files.append(os.sep.join([dirpath, filename]))
    return tiff_files


def transform_19n(input_file):
    """
    Transform from NAD83(2011) / UTM zone 19N + MLLW to NAD83(2011) / UTM zone 19N + PRVD
    """
    # Currently for Puerto Rico there is no "NAD83(2011) + MLLW" CRS is defined in the database. 
    # The closest CRS I can find is "NAD83(2011) + MSL (GEOID12B_PRVI) height": NOAA:8283 = EPSG:6318+NOAA:5535

    # Horizontal: NAD83(2011) / UTM zone 19N + MLLW  >>>>  NAD83(2011) + MLLW
    t1 = Transformer(crs_from="EPSG:26919+NOAA:5535",
                     crs_to="NOAA:8283", # NOAA:8283 = EPSG:6318+NOAA:5535
                     allow_ballpark=False
                     )
    out_file1 = pathlib.Path(input_file).with_stem("_01_8283_" + pathlib.Path(input_file).stem)
    t1.transform_raster(input_file=input_file,
                        output_file=out_file1,
                        apply_vertical=False
                        )

    # Vertical: NAD83(2011) + MSL (GEOID12B_PRVI) height >>>>  NAD83(2011) + PRVD02
    t2 = Transformer(crs_from="NOAA:8283", # NOAA:8283 = EPSG:6318+NOAA:5535
                     crs_to="EPSG:9522", #"EPSG:9522 = EPSG:6318+EPSG:6641
                     allow_ballpark=True  # have to set it to True (results in noop). Setting crs_to=NOAA:8552 also results in noop
                     )
    out_file2 = pathlib.Path(input_file).with_stem("_02_9522_" + pathlib.Path(input_file).stem)
    t2.transform_raster(input_file=out_file1,
                        output_file=out_file2,
                        apply_vertical=True
                        )

    # Project: NAD83(2011)  >>>>  NAD83(2011) / UTM zone 19N
    t3 = Transformer(crs_from="EPSG:9522", #"EPSG:9522 = EPSG:6318+EPSG:6641
                     crs_to="EPSG:26919+EPSG:6641",
                     allow_ballpark=False
                     )
    out_file3 = pathlib.Path(input_file).with_stem("_03_26919_6641_" + pathlib.Path(input_file).stem)
    t3.transform_raster(input_file=out_file2,
                        output_file=out_file3,
                        apply_vertical=False
                        )
    return




if __name__ == "__main__":
    input_files = get_tiff_files(r"W:\working_space\test_environments\sandbox\PBG19") + get_tiff_files(r"W:\working_space\test_environments\sandbox\PBG20")

    for input_file in input_files[:1]:
        print(input_file)
        get_raster_crs(input_file, verbose=True)
        transform_19n(input_file)


