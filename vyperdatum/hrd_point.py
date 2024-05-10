import numpy as np
import pyproj as pp
import rasterio
from transformer import Transformer
from utils import raster_utils

def get_band_array(raster_path: str, iband: int):
    print(f"Extracting arrays from: {raster_path} ... ")
    with rasterio.open(raster_path) as rast:
        band = rast.read(iband)
        cols, rows = np.meshgrid(np.arange(band.shape[1]), np.arange(band.shape[0]))
        xs, ys = rasterio.transform.xy(rast.transform, rows, cols)
    return np.array(xs), np.array(ys), np.array(band)


def build_transformer(crs_from: str, crs_to: str):
    return Transformer(crs_from=pp.CRS(crs_from),
                       crs_to=pp.CRS(crs_to),
                       always_xy=True,
                       allow_ballpark=False
                       )


def main(input_file):
    iband = 1
    x, y, z = get_band_array(input_file, iband)

    # metadata = raster_utils.raster_metadata(input_file)
    # x = np.where((x == metadata["band_no_data"][iband]) | (np.isnan(x)), 0, x)
    # y = np.where((y == metadata["band_no_data"][iband]) | (np.isnan(y)), 0, y)
    # z = np.where((z == metadata["band_no_data"][iband]) | (np.isnan(z)), 0, z)

    t1 = build_transformer(crs_from="EPSG:32618", crs_to="EPSG:9755")
    x1, y1, z1 = t1.transform_points(x.flatten(), y.flatten(), z.flatten())

    t2 = build_transformer(crs_from="EPSG:9755", crs_to="EPSG:6318")
    x2, y2, z2 = t2.transform_points(x1, y1, z1)

    t3 = build_transformer(crs_from="EPSG:6318+NOAA:5503", crs_to="EPSG:6318+EPSG:5703")
    # ignore the vertical shifts from the previous transformations
    x3, y3, z3 = t3.transform_points(x2, y2, z.flatten())
    return x3, y3, z3






if __name__ == "__main__":
    input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\Tile1_PBC18_4m_20211001_145447.tif"
    main(input_file)
