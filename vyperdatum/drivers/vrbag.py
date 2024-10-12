import os, time
from glob import glob
import shutil
from typing import Union
import concurrent.futures
import numpy as np
import pyproj as pp
import h5py
from tqdm import tqdm
from osgeo import gdal
from vyperdatum.transformer import Transformer
from vyperdatum.utils.raster_utils import raster_metadata
from vyperdatum.enums import VRBAG as vrb_enum


def index_to_xy(i: int, j: int, geot: tuple, x_offset, y_offset):
    """
    Take indices of a cell from the base grid and return x, y.

    Parameters
    ----------
    i: int
        Cells's first index.
    j: int
        Cells's second index.
    geot: tuple
        Gdal GeoTransform tuple object.

    Returns
    ----------
    float, float
        easting, northing
    """
    res_x, res_y = geot[1], geot[5]
    x_min, y_max = geot[0], geot[3]
    x = j * res_x + x_min + x_offset
    y = i * res_y + y_max + y_offset
    return x, y


def get_subgrids(fname: str) -> tuple[list[float], list[float], list[float], list[float]]:
    """
    Identify the subgrids within the vrbag and return the starting
    index and coordinates of the points within each subgrid.

    Parameters
    ----------
    fname: str
        Absolute path to the vrbag file.

    Returns
    ----------
    list[float], list[float], list[float], list[float]
        Starting index of each subgrid.
        x, y, z coordinates of the subgrid points.
    """
    ds_gdal = gdal.Open(fname)
    geot = ds_gdal.GetGeoTransform()
    bag = h5py.File(fname)["BAG_root"]
    vr_meta = bag["varres_metadata"]
    vr_ref = bag["varres_refinements"][0]
    index, x, y, z = [], [], [], []
    for i in tqdm(range(vr_meta.shape[0])):
        for j in range(vr_meta.shape[1]):
            start = vr_meta[i, j][0]
            if start == 0xffffffff:
                continue
            dim_x, dim_y = vr_meta[i, j][1], vr_meta[i, j][2]
            res_x, res_y = vr_meta[i, j][3], vr_meta[i, j][4]
            sw_corner_x, sw_corner_y = vr_meta[i, j][5], vr_meta[i, j][6]
            cell_x, cell_y = index_to_xy(i, j, geot, x_offset=sw_corner_x, y_offset=sw_corner_y)
            index.append(start)
            x.append(np.array([cell_x + (i - i // dim_x) * res_x for i in range(dim_x*dim_y)]))
            y.append(np.array([cell_y + (i // dim_x) * res_y for i in range(dim_x*dim_y)]))
            z.append(np.array([vr[0] for vr in vr_ref[start:start+(dim_x*dim_y)]]))
    ds_gdal = None
    return index, x, y, z


def subgrid_point_transform(x: Union[list[float], np.ndarray],
                            y: Union[list[float], np.ndarray],
                            z: Union[list[float], np.ndarray],
                            crs_from: str,
                            crs_to: str,
                            steps: list[str]
                            ) -> tuple[list[float], list[float], list[float]]:
    """
    Apply point transformation of subgrid points.

    Parameters
    ----------
    x: list[float] or np.ndarray
        Point's x-coordinate.
    y: list[float] or np.ndarray
        Point's y-coordinate.
    z: list[float] or np.ndarray
        Point's z-coordinate.
    crs_from: str
        Source CRS, in authority:code format.
    crs_to: str
        Target CRS, in authority:code format.
    steps: list[str]
        List of required intermediate CRSs to apply the
        transformation (all in authority:code format).

    Returns
    ----------
    list[float], list[float], list[float]
        x, y, z transformed coordinates of the subgrid points.
    """

    assert len(x) == len(y) == len(z)
    tf = Transformer(crs_from=crs_from,
                     crs_to=crs_to,
                     steps=steps
                     )
    xt, yt, zt = [], [], []
    for i in tqdm(range(len(x))):
        xx, yy, zz = tf.transform_points(x[i], y[i], z[i])
        xx = np.where(z[i] == vrb_enum.NDV_REF.value, x[i], xx)
        yy = np.where(z[i] == vrb_enum.NDV_REF.value, y[i], yy)
        zz = np.where(z[i] == vrb_enum.NDV_REF.value, z[i], zz)
        xt.append(xx)
        yt.append(yy)
        zt.append(zz)
    return xt, yt, zt


def single_raster_transform(tf: Transformer,
                            input_file: str,
                            output_file: str
                            ):

    try:
        tf.transform_raster(input_file=input_file, output_file=output_file,
                            pre_post_checks=False, vdatum_check=False)
        res = output_file
    except:
        res = None
    return res


def subgrid_transform(fname: str,
                      rasters_dir: str,
                      i: int,
                      j: int,
                      tf: Transformer,
                      nodata_value
                      ):
    """
    Extract a subgrid from from the vrbag file, convert to GeoTiff, and apply transformation.

    Parameters
    ----------
    fname: str
        Absolute path to the vrbag file.
    rasters_dir: str
        Absolute path to the directory where the output TIFF files will be stored.
    i: int
        First index of the subgrid.
    j: int
        Second index of the subgrid.
    tf: vyperdatum.transformer.Transformer
        Instance of the transformer class.
    nodata_value: float
        No_Data_Value used for the generated GeoTiff.

    Returns
    ----------
        The starting index of the subgrid in the varres_refinements layer.
        The transformed subgrid in form of a 1-d array.
    """
    try:
        bagm = raster_metadata(fname)
        geot = bagm["geo_transform"]
        wkt = bagm["wkt"]

        bag = h5py.File(fname)
        root = bag["BAG_root"]
        vr_meta = root["varres_metadata"]
        vr_ref = root["varres_refinements"][0]
        start = vr_meta[i, j][0]

        dim_x, dim_y = vr_meta[i, j][1], vr_meta[i, j][2]
        res_x, res_y = vr_meta[i, j][3], vr_meta[i, j][4]
        sw_corner_x, sw_corner_y = vr_meta[i, j][5], vr_meta[i, j][6]

        sub_x_min = sw_corner_x + j * geot[1]
        sub_y_min = sw_corner_y + i * abs(geot[5])
        sub_extent = [sub_x_min, sub_y_min, sub_x_min + geot[1], sub_y_min + abs(geot[5])]
        sub_geot = (sub_extent[0], res_x, 0, sub_extent[3], 0, -res_y)
        sub_grid = vr_ref[start:start+(dim_x*dim_y)]["depth"].reshape((dim_y, dim_x))

        # Save subgrid as Geotiff
        driver = gdal.GetDriverByName("GTiff")
        sub_raster_fname = f"{rasters_dir}{i}_{j}.tiff"
        out_ds = driver.Create(sub_raster_fname, sub_grid.shape[1],
                               sub_grid.shape[0], 1, gdal.GDT_Float32)
        out_ds.SetProjection(wkt)
        out_ds.SetGeoTransform(sub_geot)
        band = out_ds.GetRasterBand(1)
        band.WriteArray(sub_grid)
        band.SetNoDataValue(nodata_value)
        band.FlushCache()
        band.ComputeStatistics(False)
        out_ds = None

        #####################
        transformed_sub_fname = f"{rasters_dir}t_{i}_{j}.tiff"
        tf.transform_raster(input_file=sub_raster_fname, output_file=transformed_sub_fname,
                            pre_post_checks=False, vdatum_check=False)
        ds = gdal.Open(transformed_sub_fname)
        transformed_refs = ds.GetRasterBand(1).ReadAsArray().flatten()
        ds = None
        bag.close()
        gdal.Unlink(sub_raster_fname)
        gdal.Unlink(transformed_sub_fname)
    except Exception as e:
        print(e)
        start, transformed_refs = None, None
    return start, transformed_refs


def subgrid_raster_transform(fname: str,
                             rasters_dir: str,
                             crs_from: str,
                             crs_to: str,
                             steps: list[str]
                             ) -> tuple[list[int], list[float]]:
    """
    Identify the subgrids within the vrbag and return the starting
    index and the depth values within each subgrid.

    Parameters
    ----------
    rasters_dir : str
        Absolute path to the directory where the output TIFF files will be stored.
    crs_from: str
        Projection of input data in `authority:code` format.
    crs_to: str
        Projection of output data in `authority:code` format.
    steps: list[str]
        A list of CRSs in form of `authority:code`, representing the transformation steps
        connecting the `crs_from` to `crs_to`.
        Example: ['EPSG:6348', 'EPSG:6319', 'NOAA:8322', 'EPSG:6348+NOAA:5320']

    Returns
    ----------
    list[int], list[float]
        Starting index of each subgrid.
        Transformed subgrid depth values.
    """

    if rasters_dir.split("/")[0].lower() != "vsimem":
        if os.path.isdir(rasters_dir):
            shutil.rmtree(rasters_dir)
        os.makedirs(rasters_dir)
    bag = h5py.File(fname)
    root = bag["BAG_root"]
    vr_meta = root["varres_metadata"]
    start_indices, transformed_refs, ii, jj = [], [], [], []
    tf = Transformer(crs_from=crs_from, crs_to=crs_to, steps=steps)
    for i in tqdm(range(vr_meta.shape[0]), desc="Making subgrid rasters"):
        for j in range(vr_meta.shape[1]):
            start = vr_meta[i, j][0]
            if start == vrb_enum.NO_REF_INDEX.value:
                continue
            ii.append(i)
            jj.append(j)
    bag.close()
    with concurrent.futures.ProcessPoolExecutor() as executor:
        futureObjs = executor.map(subgrid_transform,
                                  [fname] * len(ii),
                                  [rasters_dir] * len(ii),
                                  ii, jj,
                                  [tf] * len(ii),
                                  [vrb_enum.NDV_REF.value] * len(ii)
                                  )
        for i, fo in enumerate(futureObjs):
            if fo[0] is not None:
                start_indices.append(fo[0])
                transformed_refs.append(fo[1])
    return start_indices, transformed_refs


def update_vr_refinements(fname: str,
                          index: list[int],
                          arr: list[np.ndarray]) -> None:
    """
    Update the `varres_refinements` layer in the vrbag file with the
    `arr` values starting form `index` location in the `varres_refinements`.

    Parameters
    ----------
    fname : str
        Absolute path to the vrbag file.
    index: list[int]
        A list of starting index where the refinements get updated.
    arr: list[np.ndarray]
        List of numpy array representing the refinements values to be updated.

    Returns
    ----------
    None
    """

    bag = h5py.File(fname, "r+")
    root = bag.require_group("/BAG_root")
    vr_ref = root["varres_refinements"]
    vr_ref_type = [("depth", np.float32), ("depth_uncrt", np.float32)]
    vr_ref = np.array(vr_ref, dtype=vr_ref_type)
    for i, index_start in enumerate(index):
        vr_ref[0][index_start:len(arr[i])+index_start]["depth"] = arr[i]
    del root["varres_refinements"]
    root.create_dataset("varres_refinements",
                        maxshape=(1, None),
                        data=vr_ref,
                        # fillvalue=np.array([(vrb_enum.NDV_REF.value, vrb_enum.NDV_REF.value)], dtype=vr_ref_type),
                        compression="gzip",
                        compression_opts=9
                        )
    bag.close()
    return


if __name__ == "__main__":
    fname = r"C:\Users\mohammad.ashkezari\Desktop\original_vrbag\W00656_MB_VR_MLLW_5of5.bag"

    ############ raster transformation ##############
    tic = time.time()
    crs_from = "EPSG:32617+EPSG:5866"
    crs_to = "EPSG:26917+EPSG:5866"
    steps = ["EPSG:32617+EPSG:5866", "EPSG:9755", "EPSG:6318", "EPSG:26917+EPSG:5866"]
    index, zt = subgrid_raster_transform(fname=fname,
                                        #  rasters_dir="./sub_grids/",
                                         rasters_dir="/vsimem/sub_grids/",
                                         crs_from=crs_from,
                                         crs_to=crs_to,
                                         steps=steps
                                         )
    print("total time: ", time.time() - tic)

    update_vr_refinements(fname=fname,
                          index=index,
                          arr=zt
                          )

    # # ############ point transformation ##############
    # index, x, y, z = get_subgrids(fname=fname)
    # # limit data for test
    # index, x, y, z = index[:2], x[:2], y[:2], z[:2]
    # xt, yt, zt = subgrid_point_transform(x, y, z,
    #                                      crs_from="EPSG:32617+EPSG:5866",
    #                                      crs_to="EPSG:26917+EPSG:5866",
    #                                      # steps=["EPSG:32617+EPSG:5866", "EPSG:9755+EPSG:5866", "EPSG:6318+EPSG:5866", "EPSG:26917+EPSG:5866"]
    #                                      steps=["EPSG:32617+EPSG:5866", "EPSG:9755", "EPSG:6318", "EPSG:26917+EPSG:5866"]
    #                                      )
    # update_vr_refinements(fname=fname,
    #                       index=index,
    #                       arr=zt
    #                       )
