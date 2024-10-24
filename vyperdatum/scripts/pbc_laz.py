import shutil
from vyperdatum.pipeline import Pipeline
from vyperdatum.transformer import Transformer
import laspy
import numpy as np
import pyproj as pp


def laz_coords(fname: str):
    with laspy.open(fname) as lf:
        points = lf.read()
        x = np.array(points.x)
        y = np.array(points.y)
        z = np.array(points.z)
    return x, y, z


def laz_wkt(fname):
    with laspy.open(fname) as lf:
        wkt = lf.header.parse_crs().to_wkt()
    return wkt


def transform_laz(fname, crs_from: str, crs_to: str, steps: list):
    x, y, z = laz_coords(fname)
    lf = laspy.read(fname)
    tf = Transformer(crs_from=crs_from, crs_to=crs_to, steps=steps)
    xx, yy, zz = tf.transform_points(x, y, z)
    lf.z = zz
    lf.header.add_crs(pp.CRS(crs_to))
    lf.write(fname)
    return


if __name__ == "__main__":
    in_fname = r"C:\Users\mohammad.ashkezari\Desktop\laz\ma2021_cent_east_Job1082403.laz"
    out_fname = r"C:\Users\mohammad.ashkezari\Desktop\laz\transformed_ma2021_cent_east_Job1082403.laz"
    shutil.copy2(in_fname, out_fname)
    crs_from = "EPSG:6348+EPSG:5703"
    crs_to = "EPSG:6348+NOAA:5320"
    # print(Pipeline(crs_from=crs_from, crs_to=crs_to).linear_steps())
    steps = ["EPSG:6348+EPSG:5703", "EPSG:6318+EPSG:5703", "EPSG:6318+NOAA:5320", "EPSG:6348+NOAA:5320"]
    transform_laz(fname=out_fname, crs_from=crs_from, crs_to=crs_to, steps=steps)
