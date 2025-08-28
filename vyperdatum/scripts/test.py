# from pyproj import Transformer

# # Define source and target CRS
# src_crs = "EPSG:26910"   # NAD83 / UTM zone 15N
# src_crs = "EPSG:3740"   # NAD83(HARN) / UTM zone 15N
# dst_crs = "EPSG:6339"   # NAD83(2011) / UTM zone 15N

# # Create transformer
# transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)

# # Input points (x, y)
# points = [
#     [546252.0000000009, 5025087.000000002],
#     [573641.0000000009, 5046630.000000002]
# ]

# # Transform points
# transformed_points = [transformer.transform(x, y) for x, y in points]

# # Print results
# for i, (src, dst) in enumerate(zip(points, transformed_points), start=1):
#     print(f"Point {i} from {src} -> {dst}")




#----------------------------------------------------


from osgeo import gdal
import numpy as np
import h5py
gdal.UseExceptions()

import os
import glob

def bag_to_geotiff(bag_path: str, out_path: str = None, compress: bool = True):
    """
    Convert a BAG file to GeoTIFF, replicating all bands, metadata,
    georeferencing, nodata values, etc.
    
    Parameters
    ----------
    bag_path : str
        Path to the input BAG file.
    out_path : str, optional
        Path to the output GeoTIFF file. If None, uses same name with .tif extension.
    compress : bool, optional
        Whether to apply lossless DEFLATE compression to the output GeoTIFF.
    
    Returns
    -------
    str
        Path to the written GeoTIFF file.
    """
    if out_path is None:
        out_path = os.path.splitext(bag_path)[0] + ".tif"

    # Open BAG dataset
    ds = gdal.Open(bag_path, gdal.GA_ReadOnly)
    if ds is None:
        raise IOError(f"Could not open BAG file: {bag_path}")

    # Define GeoTIFF creation options
    creation_opts = []
    if compress:
        creation_opts = [
            "TILED=YES",           # tile for efficiency
            "COMPRESS=DEFLATE",    # lossless compression
            "PREDICTOR=2"          # better for floating point
        ]

    # Translate (convert) to GeoTIFF
    gdal.Translate(
        out_path,
        ds,
        format="GTiff",
        creationOptions=creation_opts
    )

    ds = None  # close dataset
    return out_path




def read_bag_bands(bag_path: str):
    ds = gdal.Open(bag_path, gdal.GA_ReadOnly)
    if ds is None:
        raise IOError(f"Could not open BAG file: {bag_path}")
    band1 = ds.GetRasterBand(1).ReadAsArray()
    band2 = ds.GetRasterBand(2).ReadAsArray()
    return band1, band2

def get_hdf5_file_version(bag_path: str):
    with h5py.File(bag_path, "r") as f:
        libver = f.id.get_access_plist().get_libver()
        return libver


if __name__ == "__main__":
    bag_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\PBC_mixed\Manual\E01096\E01096_MB_4m_MLLW_3of7.bag"
    # b1, b2 = read_bag_bands(bag_file)
    # print("numpy version:", np.__version__)
    # print("gdal version:", gdal.__version__)
    # print(gdal.VersionInfo("BUILD_INFO"))
    # # print(get_hdf5_file_version(bag_file))
    # print(h5py.__version__)
    # print("Band 1 shape:", b1.shape, "dtype:", b1.dtype)
    # print("Band 2 shape:", b2.shape, "dtype:", b2.dtype)

    parent_dir = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\PBC_mixed\Manual\E01096\*.bag"
    files = glob.glob(parent_dir, recursive=True)[:]
    for bag_file in files:
        print("Converting BAG to GeoTIFF:", bag_file)
        tif_file = bag_to_geotiff(bag_file)
        print("GeoTIFF written to:", tif_file)    
