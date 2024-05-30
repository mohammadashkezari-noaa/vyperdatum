import os, sys, pathlib
import pyproj as pp
sys.path.append("..")
from transformer import Transformer
from utils.raster_utils import raster_metadata


def get_raster_crs(input_file: str, verbose: bool):
    meta = raster_metadata(input_file, verbose=verbose)
    input_crs = pp.CRS(meta["wkt"])
    input_horizontal_crs = pp.CRS(input_crs.sub_crs_list[0])
    input_vertical_crs = pp.CRS(input_crs.sub_crs_list[1])
    return input_crs, input_horizontal_crs, input_vertical_crs



def transform(input_file):
    """
    Transform from NAD83 / UTM zone 14N + MLLW to NAD83(2011) / UTM zone 19N + NAVD88
    """

    # Horizontal: NAD83 / UTM zone 14N + MLLW  height >>>>  NAD83(NSRS2007) + MLLW height
    t1 = Transformer(crs_from="EPSG:26914+NOAA:5498",
                     crs_to="EPSG:4759+NOAA:5498",
                     allow_ballpark=False
                     )
    out_file1 = pathlib.Path(input_file).with_stem("_01_4759_5498_" + pathlib.Path(input_file).stem)
    t1.transform_raster(input_file=input_file,
                        output_file=out_file1,
                        apply_vertical=False
                        )

    # Vertical: NAD83(NSRS2007) + MLLW height >>>>  NAD83(NSRS2007) + NAVD88
    t2 = Transformer(crs_from="EPSG:4759+NOAA:5498",
                     crs_to="EPSG:4759+EPSG:5703",
                     allow_ballpark=False
                     )
    out_file2 = pathlib.Path(input_file).with_stem("_02_4759_5703_" + pathlib.Path(input_file).stem)
    t2.transform_raster(input_file=out_file1,
                        output_file=out_file2,
                        apply_vertical=True
                        )

    # Project: NAD83(NSRS2007) + NAVD88  >>>>  NAD83 / UTM 14N + NAVD88
    t3 = Transformer(crs_from="EPSG:4759+EPSG:5703",
                     crs_to="EPSG:26914+EPSG:5703",
                     allow_ballpark=False
                     )
    out_file3 = pathlib.Path(input_file).with_stem("_03_6318_5703_" + pathlib.Path(input_file).stem)
    t3.transform_raster(input_file=out_file2,
                        output_file=out_file3,
                        apply_vertical=False
                        )
    return




if __name__ == "__main__":


    #### WKT and CRS looks Good! but it's transferred to MSL instead of NAVD88 (NAD83 / UTM zone 19N + MLLW height  >>>>>  NAD83(2011) / UTM zone 19N + MSL height)
    input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\BlueTopo\BC26J26D\Modeling_BC26J26D_20230313.tiff"
    input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\BlueTopo\BC26J26D\BlueTopo_BC26J26D_20230313.tiff"


    #### WKT and CRS looks Good! but it's transferred to MSL instead of NAVD88 (NAD83 / UTM zone 19N + MLLW height  >>>>>  NAD83(2011) / UTM zone 19N + MSL height)
    input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\BlueTopo\BH5594ZK\BlueTopo_BH5594ZK_20240304.tiff"
    input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\BlueTopo\BH5594ZK\Modeling_BH5594ZK_20240304.tiff"

    input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\BlueTopo\BC25L26L\BlueTopo_BC25L26L_20230919.tiff"
    input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\BlueTopo\BC25L26L\Modeling_BC25L26L_20230919.tiff"


    #### WKT and CRS looks Good! but it's transferred to MSL instead of NAVD88 (NAD83 / UTM zone 19N + MLLW height  >>>>>  NAD83(2011) / UTM zone 19N + MSL height)
    # ## HRD
    # input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\HRD\Tile1_PBC18_4m_20211001_145447.tif"

    # ## MSP
    # input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\MSP\Tile24_PBG16n_4m_Navigation_20231025_112416_0m_20231027_154223.tif"

    # ## MAINE-CAN
    # input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\Maine_Canada\Modeling_BH54Q5HQ_20240510.tiff"

    # ## Caribbean
    # input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\Caribbean\Modeling_BH4WT4ZK_20240307.tiff"

    get_raster_crs(input_file, verbose=True)
    # transform(input_file)


