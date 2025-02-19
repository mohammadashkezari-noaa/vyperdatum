import os
import glob
from pathlib import Path
from vyperdatum.transformer import Transformer
from vyperdatum.utils.raster_utils import raster_metadata, update_raster_wkt
from vyperdatum.utils.vdatum_rest_utils import vdatum_cross_validate
import pyproj as pp
from osgeo import gdal
import re


def get_tiff_files(parent_dir: str, extention: str) -> list:
    tiff_files = []
    for (dirpath, dirnames, filenames) in os.walk(parent_dir):
        for filename in filenames:
            if filename.endswith(extention):
                tiff_files.append(os.sep.join([dirpath, filename]))
    return tiff_files


def transform_with_vyperdatum_navd88(input_file):
    crs_from = "EPSG:6345+EPSG:5703"
    crs_to = "EPSG:6345+NOAA:93"

    steps = [
                {"crs_from": "EPSG:6345+EPSG:5703", "crs_to": "EPSG:6318+EPSG:5703", "v_shift": False},
                {"crs_from": "EPSG:6318+EPSG:5703", "crs_to": "EPSG:6318+NOAA:93", "v_shift": True},
                {"crs_from": "EPSG:6318+NOAA:93", "crs_to": "EPSG:6345+NOAA:93", "v_shift": False}
            ]
    tf = Transformer(crs_from=crs_from,
                     crs_to=crs_to,
                     steps=steps
                     )
    output_file = input_file.replace("Original", "Manual")
    tf.transform_raster(input_file=input_file,
                        output_file=output_file,
                        overview=False,
                        pre_post_checks=True,
                        vdatum_check=False
                        )

    passed, cross_df = vdatum_cross_validate(s_wkt=pp.CRS(crs_from).to_wkt(),
                                             t_wkt=pp.CRS(crs_to).to_wkt(),
                                             n_sample=20,
                                             s_raster_metadata=raster_metadata(input_file),
                                             t_raster_metadata=raster_metadata(output_file),
                                             s_point_samples=None,
                                             t_point_samples=None,
                                             tolerance=0.3,
                                             raster_sampling_band=1,
                                             region="contiguous",
                                             pivot_h_crs="EPSG:6318",
                                             s_h_frame="NAD83_2011",
                                             s_v_frame="NAVD88",
                                             s_h_zone=None,
                                             t_h_frame="NAD83_2011",
                                             t_v_frame="LWD_IGLD85",
                                             t_h_zone=None
                                             )
    cross_df.to_csv(Path(output_file).parent.absolute()/Path(f"{os.path.split(input_file)[1]}_vdatum_check.csv"), index=False)    
    return

def transform_with_vyperdatum_igld85(input_file):
    crs_from = "EPSG:6345+NOAA:92"
    crs_to = "EPSG:6345+NOAA:93"

    steps = [
                {"crs_from": "EPSG:6345+NOAA:92", "crs_to": "EPSG:6318+NOAA:92", "v_shift": False},
                {"crs_from": "EPSG:6318+NOAA:92", "crs_to": "EPSG:6318+NOAA:93", "v_shift": True},
                {"crs_from": "EPSG:6318+NOAA:93", "crs_to": "EPSG:6345+NOAA:93", "v_shift": False}
            ]
    tf = Transformer(crs_from=crs_from,
                     crs_to=crs_to,
                     steps=steps
                     )
    output_file = input_file.replace("Original", "Manual")
    tf.transform_raster(input_file=input_file,
                        output_file=output_file,
                        overview=False,
                        pre_post_checks=True,
                        vdatum_check=False
                        )

    passed, cross_df = vdatum_cross_validate(s_wkt=pp.CRS(crs_from).to_wkt(),
                                             t_wkt=pp.CRS(crs_to).to_wkt(),
                                             n_sample=20,
                                             s_raster_metadata=raster_metadata(input_file),
                                             t_raster_metadata=raster_metadata(output_file),
                                             s_point_samples=None,
                                             t_point_samples=None,
                                             tolerance=0.3,
                                             raster_sampling_band=1,
                                             region="contiguous",
                                             pivot_h_crs="EPSG:6318",
                                             s_h_frame="NAD83_2011",
                                             s_v_frame="IGLD85",
                                             s_h_zone=None,
                                             t_h_frame="NAD83_2011",
                                             t_v_frame="LWD_IGLD85",
                                             t_h_zone=None
                                             )
    cross_df.to_csv(Path(output_file).parent.absolute()/Path(f"{os.path.split(input_file)[1]}_vdatum_check.csv"), index=False)    
    return


def transform_with_concat_pipe(input_file, output_file):    
    output_vrt = output_file.replace(".tif", ".vrt")

    #projinfo -s EPSG:6347 -t EPSG:9989 --spatial-test intersects --hide-ballpark -o PROJ
    NAD83_2011_UTM18N_to_ITRF2020 = """
    +step +inv +proj=utm +zone=18 +ellps=GRS80
    +step +proj=cart +ellps=GRS80
    +step +inv +proj=helmert
        +x=1.0039 +y=-1.90961 +z=-0.54117 +rx=0.02678138 +ry=-0.00042027 +rz=0.01093206 +s=-5.109e-05
        +dx=0.00079 +dy=-0.0007 +dz=-0.00124 +drx=6.667e-05 +dry=-0.00075744 +drz=-5.133e-05 +ds=-7.201e-05
        +t_epoch=2010 +convention=coordinate_frame
    +step +inv +proj=cart +ellps=GRS80"""

    #projinfo -s EPSG:9990 -t EPSG:6347 --spatial-test intersects --hide-ballpark -o PROJ
    ITRF2020_2010_to_NAD83_2011_18N = """
    +step +proj=cart +ellps=GRS80
    +step +proj=helmert +x=1.0039 +y=-1.90961 +z=-0.54117 +rx=0.02678138
            +ry=-0.00042027 +rz=0.01093206 +s=-5.109e-05 +dx=0.00079 +dy=-0.0007
            +dz=-0.00124 +drx=6.667e-05 +dry=-0.00075744 +drz=-5.133e-05 +ds=-7.201e-05
            +t_epoch=2010 +convention=coordinate_frame
    +step +inv +proj=cart +ellps=GRS80
    +step +proj=utm +zone=18 +ellps=GRS80"""

    MLLW_ITRF2020_2020 = "us_noaa_nos_MLLW-ITRF2020_2020.0_(nwldatum_4.7.0_20240621).tif"

    gdal_warp_concatenated_transform = f"""\
    +proj=pipeline
    {NAD83_2011_UTM18N_to_ITRF2020}
    +step +inv +proj=vgridshift +grids={MLLW_ITRF2020_2020} +multiplier=1
    +step +proj=push +v_3
    {ITRF2020_2010_to_NAD83_2011_18N}
    +step +proj=pop +v_3"""

    # output pixel resolution = input pixel resolution
    with gdal.Open(input_file, gdal.GA_ReadOnly) as input_ds:
        geotransform = input_ds.GetGeoTransform()
        xres, yres = geotransform[1], geotransform[5]

    # create vrt transformation template dataset
    ds = gdal.Warp(output_vrt, input_file, format="vrt", outputType=gdal.gdalconst.GDT_Float32,warpOptions = ["APPLY_VERTICAL_SHIFT=YES", "SAMPLE_GRID=YES", "SAMPLE_STEPS=ALL"], errorThreshold = 0, xRes=xres, yRes=yres, targetAlignedPixels=True, coordinateOperation=gdal_warp_concatenated_transform)
    # remove whitespace formatting used in proj pipeline string and put it in GeoTIFF metadata
    gdal_warp_concatenated_transform = re.sub(r'\s{2,}', ' ', gdal_warp_concatenated_transform).strip()
    ds.SetMetadataItem('TIFFTAG_IMAGEDESCRIPTION', gdal_warp_concatenated_transform)

    # execute the transformation from the vrt dataset to output compressed tif
    output_ds = gdal.Translate(output_file, ds, format="GTiff", outputType=gdal.GDT_Float32, creationOptions=["COMPRESS=DEFLATE", "TILED=YES"])
    output_ds = None    
    return




if __name__ == "__main__":
    files = glob.glob(r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\PBD\Original\NAVD88\**\*.tif", recursive=True)
    files = glob.glob(r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\PBD\Original\IGLD85\**\*.tif", recursive=True)



    for i, input_file in enumerate(files[:]):
        print(f"{i+1}/{len(files)}: {input_file}")
        # transform_with_vyperdatum_navd88(input_file)
        transform_with_vyperdatum_igld85(input_file)

        ###########################
        # try:
        #     crs_from = "EPSG:6345+NOAA:92"
        #     crs_to = "EPSG:6345+NOAA:93"
        #     output_file = input_file.replace("Original", "Manual")
        #     Path(os.path.split(output_file)[0]).mkdir(parents=True, exist_ok=True)
        #     transform_with_concat_pipe(input_file, output_file)
        #     update_raster_wkt(output_file, pp.CRS(crs_to).to_wkt())
        #     passed, cross_df = vdatum_cross_validate(s_wkt=pp.CRS(crs_from).to_wkt(),
        #                                              t_wkt=pp.CRS(crs_to).to_wkt(),
        #                                              n_sample=20,
        #                                              s_raster_metadata=raster_metadata(input_file),
        #                                              t_raster_metadata=raster_metadata(output_file),
        #                                              s_point_samples=None,
        #                                              t_point_samples=None,
        #                                              tolerance=0.3,
        #                                              raster_sampling_band=1,
        #                                              region="contiguous",
        #                                              pivot_h_crs="EPSG:6318",
        #                                              s_h_frame="NAD83_2011",
        #                                              s_v_frame="IGLD85",
        #                                              s_h_zone=None,
        #                                              t_h_frame="NAD83_2011",
        #                                              t_v_frame="LWD_IGLD85",
        #                                              t_h_zone=None
        #                                              )
        #     cross_df.to_csv(Path(output_file).parent.absolute()/Path(f"{os.path.split(input_file)[1]}_vdatum_check.csv"), index=False)
        # except Exception as e:
        #         efile = open(Path(output_file).parent.absolute()/Path(f"{os.path.split(input_file)[1]}_error.txt"), "w")
        #         efile.write(str(e))
        #         efile.close()

        ###########################

        print(f'\n{"*"*50} {i+1}/{len(files)} Completed {"*"*50}\n')
