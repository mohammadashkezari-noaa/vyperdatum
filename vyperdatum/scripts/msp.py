import pathlib
import pyproj as pp
from vyperdatum.transformer import Transformer
from vyperdatum.utils.raster_utils import raster_metadata


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


def transform_16n(input_file):
    # Horizontal: NAD83(2011) / UTM zone 16N + MLLW  >>>>  NAD83(2011) + MLLW
    t1 = Transformer(crs_from="EPSG:26916+NOAA:5447",
                     crs_to="NOAA:8449", #"EPSG:6318+NOAA:5447",  # same as NOAA:8449
                     allow_ballpark=False
                     )
    out_file1 = pathlib.Path(input_file).with_stem("_01_8449_" + pathlib.Path(input_file).stem)
    t1.transform_raster(input_file=input_file,
                        output_file=out_file1,
                        apply_vertical=False
                        )

    # Vertical: NAD83(2011) + MLLW >>>>  NAD83(2011) + NAVD88
    t2 = Transformer(crs_from="NOAA:8449", #"EPSG:6318+NOAA:5447",  # same as NOAA:8449
                     crs_to="EPSG:6349", #"EPSG:6318+EPSG:5703",    # same as EPSG:6349
                     allow_ballpark=False
                     )
    out_file2 = pathlib.Path(input_file).with_stem("_02_6349_" + pathlib.Path(input_file).stem)
    t2.transform_raster(input_file=out_file1,
                        output_file=out_file2,
                        apply_vertical=True
                        )

    # Project: NAD83(2011)  >>>>  NAD83(2011) / UTM zone 16N
    t3 = Transformer(crs_from="EPSG:6349", #"EPSG:6318+EPSG:5703",
                     crs_to="EPSG:26916+EPSG:5703",
                     allow_ballpark=False
                     )
    out_file3 = pathlib.Path(input_file).with_stem("_03_26916_5703_" + pathlib.Path(input_file).stem)
    t3.transform_raster(input_file=out_file2,
                        output_file=out_file3,
                        apply_vertical=False
                        )
    return



def transform_15n(input_file):
    # Horizontal: NAD83(2011) / UTM zone 15N + MLLW  >>>>  NAD83(2011) + MLLW
    t1 = Transformer(crs_from="EPSG:26915+NOAA:5447",
                     crs_to="NOAA:8449", #"EPSG:6318+NOAA:5447",  # same as NOAA:8449
                     allow_ballpark=False
                     )
    out_file1 = pathlib.Path(input_file).with_stem("_01_8449_" + pathlib.Path(input_file).stem)
    t1.transform_raster(input_file=input_file,
                        output_file=out_file1,
                        apply_vertical=False
                        )

    # Vertical: NAD83(2011) + MLLW >>>>  NAD83(2011) + NAVD88
    t2 = Transformer(crs_from="NOAA:8449", #"EPSG:6318+NOAA:5447",  # same as NOAA:8449
                     crs_to="EPSG:6349", #"EPSG:6318+EPSG:5703",    # same as EPSG:6349
                     allow_ballpark=False
                     )
    out_file2 = pathlib.Path(input_file).with_stem("_02_6349_" + pathlib.Path(input_file).stem)
    t2.transform_raster(input_file=out_file1,
                        output_file=out_file2,
                        apply_vertical=True
                        )

    # Project: NAD83(2011)  >>>>  NAD83(2011) / UTM zone 15N
    t3 = Transformer(crs_from="EPSG:6349", #"EPSG:6318+EPSG:5703",
                     crs_to="EPSG:26915+EPSG:5703",
                     allow_ballpark=False
                     )
    out_file3 = pathlib.Path(input_file).with_stem("_03_26915_5703_" + pathlib.Path(input_file).stem)
    t3.transform_raster(input_file=out_file2,
                        output_file=out_file3,
                        apply_vertical=False
                        )
    return


if __name__ == "__main__":
    input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\MSP\Tile24_PBG16n_4m_Navigation_20231025_112416_0m_20231027_154223.tif"
    get_raster_crs(input_file, verbose=True)
    # transform_16n(input_file)

    # input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\MSP\Tile59_PBG15n_4m_Navigation_20240103_094636_0m_20240103_113227.tif"
    # get_raster_crs(input_file, verbose=True)
    # transform_15n(input_file)
