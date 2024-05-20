import sys, pathlib
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


def main(input_file):
    # Horizontal: WGS 84 / UTM zone 18N  >>>>  WGS 84 (G2139)
    t1 = Transformer(crs_from="EPSG:32618+NOAA:5503",
                     crs_to="EPSG:9755+NOAA:5503",
                     allow_ballpark=False
                     )
    out_file1 = pathlib.Path(input_file).with_stem("_01_9755_" + pathlib.Path(input_file).stem)
    t1.transform_raster(input_file=input_file,
                        output_file=out_file1,
                        apply_vertical=False,
                        from_epoch=2010.0,
                        to_epoch=2010.0
                        )

    # Horizontal: WGS 84 (G2139)  >>>>  NAD83(2011)
    t2 = Transformer(
                    ### pyproj TransformerGroup doesn't accept the followings, unlike gdal warp!!
                    #  crs_from="EPSG:9755+NOAA:5503",
                    #  crs_to="EPSG:6318+NOAA:5503",
                     crs_from="EPSG:9755",
                     crs_to="EPSG:6318",
                     allow_ballpark=False
                     )
    out_file2 = pathlib.Path(input_file).with_stem("_02_6318_" + pathlib.Path(input_file).stem)
    t2.transform_raster(input_file=out_file1,
                        output_file=out_file2,
                        apply_vertical=False,
                        from_epoch=2010.0,
                        to_epoch=2010.0
                        )

    # Vertical: HRD (NOAA:5503)  >>>>  NAVD88 (EPSG:5703)
    t3 = Transformer(crs_from="EPSG:6318+NOAA:5503",
                     crs_to="EPSG:6318+EPSG:5703",
                     allow_ballpark=False
                     )
    out_file3 = pathlib.Path(input_file).with_stem("_03_6318_5703_" + pathlib.Path(input_file).stem)
    t3.transform_raster(input_file=out_file2,
                        output_file=out_file3,
                        apply_vertical=True
                        )
    return


if __name__ == "__main__":
    input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\HRD\Tile1_PBC18_4m_20211001_145447.tif"
    get_raster_crs(input_file, verbose=True)
    main(input_file)
