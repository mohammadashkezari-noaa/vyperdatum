from vyperdatum.transformer import Transformer
from glob import glob
import numpy as np
from osgeo import gdal
import os
import tempfile
import shutil

gdal.UseExceptions()


# def update_stats(input_file):
#     """
#     Update statistics for the raster file.

#     Parameters:
#         input_file (str): Path to the raster file.
#     """
#     ds = gdal.Open(input_file, gdal.GA_Update)
#     for i in range(1, ds.RasterCount + 1):
#         ds.GetRasterBand(i).ComputeStatistics(False)
#     ds = None  # flush
#     return


# def rename_first_band(raster_path, new_name):
#     ds = gdal.Open(raster_path, gdal.GA_Update)
#     if ds is None:
#         raise RuntimeError(f"Could not open file: {raster_path}")

#     band = ds.GetRasterBand(1)
#     band.SetDescription(new_name)

#     band.FlushCache()
#     ds = None
#     return


# def add_uncertainty_band_overwrite(raster_path):
#     src_ds = gdal.Open(raster_path)
#     if src_ds is None:
#         raise RuntimeError(f"Could not open {raster_path}")

#     elev_band = src_ds.GetRasterBand(1)
#     nodata_val = elev_band.GetNoDataValue()
#     elevation = elev_band.ReadAsArray().astype(np.float32)

#     if nodata_val is not None:
#         mask = (elevation == nodata_val)
#     else:
#         mask = np.zeros_like(elevation, dtype=bool)

#     uncertainty = 1 + 0.02 * elevation
#     uncertainty[mask] = nodata_val if nodata_val is not None else 0

#     cols = src_ds.RasterXSize
#     rows = src_ds.RasterYSize
#     count = src_ds.RasterCount
#     geotransform = src_ds.GetGeoTransform()
#     projection = src_ds.GetProjection()
#     dtype = gdal.GDT_Float32

#     # Temp uncompressed file with extra band
#     tmp_uncompressed = tempfile.NamedTemporaryFile(suffix='.tif', delete=False)
#     tmp_uncompressed_path = tmp_uncompressed.name
#     tmp_uncompressed.close()

#     driver = gdal.GetDriverByName('GTiff')
#     raw_ds = driver.Create(tmp_uncompressed_path, cols, rows, count + 1, dtype)
#     raw_ds.SetGeoTransform(geotransform)
#     raw_ds.SetProjection(projection)

#     for i in range(count):
#         band = src_ds.GetRasterBand(i + 1)
#         data = band.ReadAsArray()
#         out_band = raw_ds.GetRasterBand(i + 1)
#         out_band.WriteArray(data)
#         out_band.SetDescription(band.GetDescription())
#         nd = band.GetNoDataValue()
#         if nd is not None:
#             out_band.SetNoDataValue(nd)

#     # Add uncertainty band
#     unc_band = raw_ds.GetRasterBand(count + 1)
#     unc_band.WriteArray(uncertainty)
#     unc_band.SetDescription("uncertainty")
#     if nodata_val is not None:
#         unc_band.SetNoDataValue(nodata_val)
#     unc_band.FlushCache()

#     raw_ds = None
#     src_ds = None

#     # Compress and overwrite using gdal.Translate
#     gdal.Translate(
#         destName=raster_path,
#         srcDS=tmp_uncompressed_path,
#         creationOptions=[
#             "COMPRESS=DEFLATE",
#             "TILED=YES",
#             "BIGTIFF=IF_SAFER"
#         ],
#         format="GTiff"
#     )

#     # Clean up
#     os.remove(tmp_uncompressed_path)
#     return

crs_from = "EPSG:6348"
crs_to = "EPSG:6348+NOAA:98"

input_files = glob(r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\RSD\ME\Original\**\*.tif", recursive=True)
for i, input_file in enumerate(input_files):
    print(f"Processing ({i}/{len(input_files)}): {input_file}")
    try:
        output_file = input_file.replace("Original", "Manual")
        tf = Transformer(crs_from=crs_from,
                        crs_to=crs_to,
                        )
        tf.transform(input_file=input_file,
                    output_file=output_file,
                    pre_post_checks=True,
                    vdatum_check=True
                    )
        # rename_first_band(output_file, "elevation")
        # add_uncertainty_band_overwrite(output_file)
        # update_stats(output_file)
    except Exception as e:
        print(f"Error processing {input_file}: {e}")
        continue