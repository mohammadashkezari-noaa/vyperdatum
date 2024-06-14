import sys, pathlib
sys.path.append("..")
from transformer import Transformer
from utils.raster_utils import raster_metadata
from osgeo import gdal



def transform(input_file):
    """
    Transform from NAD83 / UTM zone 14N + MLLW to NAD83(2011) / UTM zone 19N + NAVD88
    """

    warp_kwargs_vertical = {
                            "outputType": gdal.gdalconst.GDT_Float32,
                            "srcBands": [1],
                            "dstBands": [1],
                            "warpOptions": ["APPLY_VERTICAL_SHIFT=YES"],
                            "errorThreshold": 0,
                            }
    warp_kwargs = {
                   "outputType": gdal.gdalconst.GDT_Float32,
                   "warpOptions": ["APPLY_VERTICAL_SHIFT=NO"],
                   "errorThreshold": 0,
                   }

    # Horizontal: NAD83 / UTM zone 14N + MLLW  height >>>>  NAD83(NSRS2007) + MLLW height
    t1 = Transformer(crs_from="EPSG:26914+NOAA:5498",
                     crs_to="EPSG:4759+NOAA:5498",
                     allow_ballpark=False
                     )
    print(f"t1: {t1.transformer.to_proj4()}\n{'-'*40}")
    out_file1 = pathlib.Path(input_file).with_stem("_01_4759_5498_" + pathlib.Path(input_file).stem)
    t1.transform_raster(input_file=input_file,
                        output_file=out_file1,
                        apply_vertical=False,
                        )

    # Vertical: NAD83(NSRS2007) + MLLW height >>>>  NAD83(NSRS2007) + NAVD88
    t2 = Transformer(crs_from="EPSG:4759+NOAA:5498",
                     crs_to="EPSG:4759+EPSG:5703",
                     allow_ballpark=False
                     )
    print(f"t2: {t2.transformer.to_proj4()}\n{'-'*40}")
    out_file2 = pathlib.Path(input_file).with_stem("_02_4759_5703_" + pathlib.Path(input_file).stem)
    t2.transform_raster(input_file=out_file1,
                        output_file=out_file2,
                        apply_vertical=True,
                        warp_kwargs=warp_kwargs_vertical
                        )

    # Project: NAD83(NSRS2007) + NAVD88  >>>>  NAD83 / UTM 14N + NAVD88
    t3 = Transformer(crs_from="EPSG:4759+EPSG:5703",
                     crs_to="EPSG:26914+EPSG:5703",
                     allow_ballpark=False
                     )
    print(f"t3: {t3.transformer.to_proj4()}\n{'-'*40}")
    out_file3 = pathlib.Path(input_file).with_stem("_03_6318_5703_" + pathlib.Path(input_file).stem)
    t3.transform_raster(input_file=out_file2,
                        output_file=out_file3,
                        apply_vertical=False
                        )
    return out_file3


if __name__ == "__main__":
    input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\BlueTopo\BC25L26L\Modeling_BC25L26L_20230919.tiff"
    input_meta = raster_metadata(input_file, verbose=True)
    print(input_meta)
    transformed_file = transform(input_file)
    # transformed_meta = raster_metadata(transformed_file, verbose=True)
    # print(f"Input Stats: {input_meta['band_stats']}")
    # print(f"Transformed Stats: {transformed_meta['band_stats']}")

"""
The existing vyperdatum does this transformation a bit differently:
First, it recognizes that the raster file covers two regions and then perform the following transformations:

+proj=pipeline +step +inv +proj=vgridshift grids=TXlagmat01_8301\mllw.gtx +step +proj=vgridshift grids=TXlagmat01_8301\tss.gtx
----------------------------------------
+proj=pipeline +step +inv +proj=vgridshift grids=TXshlmat01_8301\mllw.gtx +step +proj=vgridshift grids=TXshlmat01_8301\tss.gtx
----------------------------------------




In the new system, the two Texas regions are defined by one 'extent' called: 'TXcoast01' (extent id: 17106)
The followings are the 3-step transformations:

t1: +proj=pipeline +step +inv +proj=utm +zone=14 +ellps=GRS80 +step +proj=gridshift +grids=us_noaa_nadcon5_nad83_1986_nad83_harn_conus.tif +step +proj=gridshift +no_z_transform +grids=us_noaa_nadcon5_nad83_harn_nad83_fbn_conus.tif +step +proj=gridshift +no_z_transform +grids=us_noaa_nadcon5_nad83_fbn_nad83_2007_conus.tif +step +proj=unitconvert +xy_in=rad +xy_out=deg +step +proj=axisswap +order=2,1

t2: +proj=pipeline +step +proj=axisswap +order=2,1 +step +proj=unitconvert +xy_in=deg +xy_out=rad +step +inv +proj=vgridshift +grids=us_noaa_nos_NAD83(NSRS2007)_MLLW_LMSL_(Txcoast01_vdatum_2.3.4_20120629_1983-2001).tif +multiplier=1 +step +inv +proj=vgridshift +grids=us_noaa_nos_NAD83(NSRS2007)_LMSL_NAVD88_(Txcoast01_vdatum_2.3.4_20120629_1983-2001).tif +multiplier=1 +step +proj=unitconvert +xy_in=rad +xy_out=deg +step +proj=axisswap +order=2,1

t3: +proj=pipeline +step +proj=axisswap +order=2,1 +step +proj=unitconvert +xy_in=deg +xy_out=rad +step +inv +proj=gridshift +no_z_transform +grids=us_noaa_nadcon5_nad83_fbn_nad83_2007_conus.tif +step +inv +proj=gridshift +no_z_transform +grids=us_noaa_nadcon5_nad83_harn_nad83_fbn_conus.tif +step +inv +proj=gridshift +grids=us_noaa_nadcon5_nad83_1986_nad83_harn_conus.tif +step +proj=utm +zone=14 +ellps=GRS80




Potential Sources of Discrepancies Between the Past and New Transformations:
- Horizontal transformations to/from NAD83(NSRS2007)
- Broadly, different proj pipelines (involving different grid files)
- Potential unidentified gdal.Warp issues (such as missing/incorrect options etc ...)
- Ongoing PROJ 'unable to compute output bounds' errors.
"""