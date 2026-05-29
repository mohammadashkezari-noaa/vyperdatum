
import os
os.environ["VYPER_GRIDS"] = r"C:\Users\Mohammad.Ashkezari\Documents\projects\vyperdatum\untrack\vyper_grids"


import glob
from datetime import datetime
import pyproj as pp

from vyperdatum.transformer import Transformer
from vyperdatum.utils.raster_utils import raster_metadata, update_raster_wkt
from vyperdatum.utils.vdatum_rest_utils import vdatum_cross_validate

from raster_arrays import RasterArrays



if __name__ == "__main__":

    files = [
        r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\PBG\Original\W00653\W00653_MB_VR_MLLW_1of3.bag",
        r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\PBG\Original\W00653\W00653_MB_VR_MLLW_3of3.bag",
             ]

    for i, input_file in enumerate(files):
        print(f"{i+1}/{len(files)}: {input_file}")

        if i == 0:
             crs_from = "EPSG:6344"
             crs_to = "EPSG:6345"
        elif i == 1:
             crs_from = "EPSG:6345"
             crs_to = "EPSG:6344"

        tic = datetime.now()
        tf = Transformer(crs_from=crs_from,
                         crs_to=crs_to
                         )
        output_file = input_file.replace("Original", "Manual").replace(".bag", ".parquet")
        ra = RasterArrays(input_file)
        try:
            ra.transform(tf, output_file=output_file)
        finally:
            ra.cleanup()
        toc = datetime.now()
        print(f"Time taken: {toc - tic}")
        print(f'\n{"*"*50} {i+1}/{len(files)} Completed {"*"*50}\n')
