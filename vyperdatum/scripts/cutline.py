import glob
from vyperdatum.transformer import Transformer
from vyperdatum.utils.raster_utils import raster_metadata, update_raster_wkt
from vyperdatum.utils.vdatum_rest_utils import vdatum_cross_validate
import pyproj as pp


def _single_xform(input_file, crs_from, crs_to):
    print(f"Transforming: {input_file}")
    tf = Transformer(crs_from=crs_from, crs_to=crs_to)
    output_file = input_file.replace("Original", "Manual")
    tf.transform_raster(input_file=input_file,
                        output_file=output_file,
                        overview=False,
                        pre_post_checks=True,
                        vdatum_check=False
                        )    


if __name__ == "__main__":

    home = r"C:\Users\mohammad.ashkezari\Desktop\Ex_Laptop\cutline\Original"

    input_file = f"{home}\BlueTopo_BH52B5FW_20250513_155731_base.tiff"
    _single_xform(input_file, crs_from="EPSG:26919+NOAA:98", crs_to="EPSG:26919+EPSG:5703")

    input_file = f"{home}2018_525000e_2785000n_tpu.tif"
    _single_xform(input_file, crs_from="EPSG:6346", crs_to="EPSG:6346+NOAA:98")

    input_file = f"{home}\2018_530000e_2785000n_tpu.tif"
    _single_xform(input_file, crs_from="EPSG:6346", crs_to="EPSG:6346+NOAA:98")

    # input_file = f"{home}\merged_BlueTopo_BH2SW5PH_20260303_172924_base.tiff"
    # _single_xform(input_file, crs_from="EPSG:26908+NOAA:98", crs_to="EPSG:26908+EPSG:5703")

    input_file = f"{home}\Tile40_PBD16n_GreatLakes_16m_Navigation_20250715_141023_10000m_20250716_122452.tif"
    _single_xform(input_file, crs_from="EPSG:26916+NOAA:101", crs_to="EPSG:26916+EPSG:5703")
