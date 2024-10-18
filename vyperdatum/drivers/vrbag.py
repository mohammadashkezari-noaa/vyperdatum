import os, time
import logging
import shutil
from typing import Union, Optional
import concurrent.futures
import numpy as np
import pyproj as pp
import h5py
from tqdm import tqdm
from osgeo import gdal
from vyperdatum.transformer import Transformer
from vyperdatum.utils.raster_utils import raster_metadata
from vyperdatum.enums import VRBAG as vrb_enum

logger = logging.getLogger("root_logger")
gdal.UseExceptions()


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


def base_grid_point_transform(fname: str,
                              tf: Transformer,
                              nodata_value
                              ) -> np.ndarray:
    """
    Transform the low-resolution grid and return the transformed values.

    Parameters
    ----------
    fname: str
        Absolute path to the vrbag file.
    tf: vyperdatum.transformer.Transformer
        Instance of the transformer class.
    nodata_value: float
        No_Data_Value used in the vrbag elevation layer.

    Returns
    ----------
    np.ndarray
        The transformed vrbag elevation layer.
    """
    ds_gdal = gdal.Open(fname)
    geot = ds_gdal.GetGeoTransform()
    bag = h5py.File(fname)
    root = bag["BAG_root"]
    vr_elev = np.array(root["elevation"])
    vr_elev_shape = vr_elev.shape
    x, y, z = np.array([]), np.array([]), np.array([])
    for i in range(vr_elev_shape[0]):
        for j in range(vr_elev_shape[1]):
            _x, _y = index_to_xy(i, j, geot, x_offset=0, y_offset=0)
            x = np.append(x, [_x])
            y = np.append(y, [_y])
            z = np.append(z, vr_elev[i, j])

    _, _, zz = tf.transform_points(x, y, z)
    zz = np.where(z == nodata_value, z, zz)
    zz = zz.reshape(vr_elev_shape)

    ds_gdal = None
    bag.close()
    return zz


def update_vr_elevation(fname: str,
                        arr: np.ndarray) -> None:
    """
    Update the `elevation` layer in the vrbag file with the `arr` values.

    Parameters
    ----------
    fname : str
        Absolute path to the vrbag file.
    arr: np.ndarray
        numpy array representing the elevation values to be updated.

    Returns
    ----------
    None
    """

    bag = h5py.File(fname, "r+")
    root = bag.require_group("/BAG_root")
    del root["elevation"]
    root.create_dataset("elevation",
                        maxshape=(None, None),
                        data=np.array(arr, dtype=np.float32),
                        fillvalue=vrb_enum.NDV_REF.value,
                        compression="gzip",
                        compression_opts=9
                        )
    arr = np.where(arr == vrb_enum.NDV_REF.value, np.nan, arr)
    root["elevation"].attrs.create("Maximum Elevation Value", np.nanmax(arr), dtype=np.float32)
    root["elevation"].attrs.create("Minimum Elevation Value", np.nanmin(arr), dtype=np.float32)
    bag.close()
    return


def get_subgrid_points(fname: str, i: int, j: int) -> tuple[list[int], list[float],
                                                            list[float], list[float]]:
    """
    Return the starting index and coordinates of the points of subgrid i, j.

    Parameters
    ----------
    fname: str
        Absolute path to the vrbag file.
    i: int
        First index of the subgrid.
    j: int
        Second index of the subgrid.

    Returns
    ----------
    list[int], list[float], list[float], list[float]
        Starting index of subgrid.
        x, y, z coordinates of the subgrid points.
    """
    ds_gdal = gdal.Open(fname)
    geot = ds_gdal.GetGeoTransform()
    bag = h5py.File(fname)
    root = bag["BAG_root"]
    vr_meta = root["varres_metadata"]
    vr_ref = root["varres_refinements"][0]

    start = vr_meta[i, j][0]
    dim_x, dim_y = vr_meta[i, j][1], vr_meta[i, j][2]
    res_x, res_y = vr_meta[i, j][3], vr_meta[i, j][4]
    sw_corner_x, sw_corner_y = vr_meta[i, j][5], vr_meta[i, j][6]
    cell_x, cell_y = index_to_xy(i, j, geot, x_offset=sw_corner_x, y_offset=sw_corner_y)

    x = np.array([cell_x + (i - i // dim_x) * res_x for i in range(dim_x*dim_y)])
    y = np.array([cell_y + (i // dim_x) * res_y for i in range(dim_x*dim_y)])
    z = np.array([vr[0] for vr in vr_ref[start:start+(dim_x*dim_y)]])
    
    ds_gdal = None
    bag.close()
    return start, x, y, z


def single_subgrid_point_transform(fname: str,
                                   i: int,
                                   j: int,
                                   tf: Transformer,
                                   nodata_value
                                   ) -> tuple[Optional[int], Optional[np.ndarray]]:
    """
    Apply point transformation of subgrid points.

    Parameters
    ----------
    fname: str
        Absolute path to the vrbag file.
    i: int
        The first index of the subgrid.
    j: int
        The second index of the subgrid.
    tf: vyperdatum.transformer.Transformer
        Instance of the transformer class.
    nodata_value: float
        No_Data_Value used for the generated GeoTiff.

    Returns
    ----------
    tuple[Optional[int], np.ndarray]
        The starting index of the subgrid in the varres_refinements layer.
        The transformed subgrid depth values in form of a 1-d array.
    """
    try:
        start, x, y, z = get_subgrid_points(fname, i, j)
        _, _, zz = tf.transform_points(x, y, z)
        zz = np.where(z == nodata_value, z, zz)
    except Exception as e:
        logger.exception(f"Unexpected exception in single_subgrid_point_transform for subgrid {i}, {j}: {e}")

        f = open("error.txt", "a")
        f.write(f"Unexpected exception in single_subgrid_point_transform for subgrid {i}, {j}: {e}\n")
        f.close()

        start, zz = None, None

    return start, zz


def subgrid_point_transform(fname: str,
                            tf: Transformer,
                            ) -> tuple[list[int], list[float]]:
    """
    Identify the subgrids within the vrbag and return the starting
    index and the depth values within each subgrid.

    Parameters
    ----------
    fname: str
        Absolute path to the vrbag file.
    tf: vyperdatum.transformer.Transformer
        Instance of the transformer class.

    Returns
    ----------
    list[int], list[float]
        Starting index of each subgrid.
        Transformed subgrid depth values.
    """
    bag = h5py.File(fname)
    root = bag["BAG_root"]
    vr_meta = root["varres_metadata"]
    start_indices, transformed_refs, ii, jj = [], [], [], []    
    for i in tqdm(range(vr_meta.shape[0]), desc="Search for refined subgrids"):
        for j in range(vr_meta.shape[1]):
            start = vr_meta[i, j][0]
            if start == vrb_enum.NO_REF_INDEX.value:
                continue
            # if not(i==11 and j==112):
            #     continue
            ii.append(i)
            jj.append(j)
    bag.close()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futureObjs = executor.map(single_subgrid_point_transform,
                                  [fname] * len(ii),
                                  ii, jj,
                                  [tf] * len(ii),
                                  [vrb_enum.NDV_REF.value] * len(ii)
                                  )
        for i, fo in enumerate(tqdm(futureObjs, total=len(ii))):
            if fo[0] is not None:
                start_indices.append(fo[0])
                transformed_refs.append(fo[1])
    return start_indices, transformed_refs


def single_subgrid_rsater_transform(fname: str,
                                    rasters_dir: str,
                                    i: int,
                                    j: int,
                                    tf: Transformer,
                                    nodata_value
                                    ) -> tuple[Optional[int], Optional[np.ndarray]]:
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
        bm = raster_metadata(fname)
        geot = bm["geo_transform"]
        wkt = bm["wkt"]

        bag = h5py.File(fname)
        root = bag["BAG_root"]
        vr_meta = root["varres_metadata"]
        vr_ref = root["varres_refinements"][0]
        start = vr_meta[i, j][0]

        dim_x, dim_y = vr_meta[i, j][1], vr_meta[i, j][2]
        res_x, res_y = vr_meta[i, j][3], vr_meta[i, j][4]
        sw_corner_x, sw_corner_y = vr_meta[i, j][5], vr_meta[i, j][6]

        sub_x_min = geot[0] + j * geot[1] + sw_corner_x
        sub_y_min = geot[3] + i * geot[5] + sw_corner_y
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

        if len(transformed_refs) != dim_y * dim_x:
            msg = f"Transferred length for sub array {i}, {j} was expected to be {dim_y * dim_x} but is {len(transformed_refs)}\n"
            logger.error(msg)
            f = open("error.txt", "a")
            f.write(msg)
            f.close()

    except Exception as e:        
        logger.exception(f"Unexpected exception in single_subgrid_rsater_transform: {e}")

        f = open("error.txt", "a")
        f.write(f"Unexpected exception in single_subgrid_rsater_transform for subgrid {i}, {j}: {e}\n")
        f.close()

        start, transformed_refs = None, None
    return start, transformed_refs


def subgrid_raster_transform(fname: str,
                             rasters_dir: str,
                             tf: Transformer,
                             ) -> tuple[list[int], list[float]]:
    """
    Identify the subgrids within the vrbag and return the starting
    index and the depth values within each subgrid.

    Parameters
    ----------
    fname : str
        Absolute path to the vrbag file.
    rasters_dir : str
        Absolute path to the directory where the output TIFF files will be stored.
    tf: vyperdatum.transformer.Transformer
        Instance of the transformer class.

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
    for i in tqdm(range(vr_meta.shape[0]), desc="Making subgrid rasters"):
        for j in range(vr_meta.shape[1]):
            start = vr_meta[i, j][0]
            if start == vrb_enum.NO_REF_INDEX.value:
                continue


            # if not(i==11 and j==112):
            #     continue        


            ii.append(i)
            jj.append(j)
    bag.close()
    with concurrent.futures.ProcessPoolExecutor() as executor:
        futureObjs = executor.map(single_subgrid_rsater_transform,
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
                          arr: list[np.ndarray],
                          tf: Transformer) -> None:
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
    tf: vyperdatum.transformer.Transformer
        Instance of the transformer class.

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
    darr = np.array(vr_ref[0][:]["depth"])
    uarr = np.array(vr_ref[0][:]["depth_uncrt"])
    darr = np.where(darr == vrb_enum.NDV_REF.value, np.nan, darr)
    uarr = np.where(uarr == vrb_enum.NDV_REF.value, np.nan, uarr)
    root["varres_refinements"].attrs.create("max_depth", np.nanmax(darr), dtype=np.float32)
    root["varres_refinements"].attrs.create("max_uncrt", np.nanmax(uarr), dtype=np.float32)
    root["varres_refinements"].attrs.create("min_depth", np.nanmin(darr), dtype=np.float32)
    root["varres_refinements"].attrs.create("min_uncrt", np.nanmin(uarr), dtype=np.float32)
    bag.close()
    # update the base grid and its attributes
    zt = base_grid_point_transform(fname=fname, tf=tf, nodata_value=vrb_enum.NDV_REF.value)
    update_vr_elevation(fname=fname, arr=zt)
    return


if __name__ == "__main__":
    fname = r"C:\Users\mohammad.ashkezari\Desktop\original_vrbag\W00656_MB_VR_MLLW_5of5.bag"
    ############ raster transformation ##############
    tic = time.time()
    crs_from = "EPSG:32617+EPSG:5866"
    crs_to = "EPSG:26917+EPSG:5866"
    # steps=["EPSG:32617+EPSG:5866", "EPSG:9755+EPSG:5866", "EPSG:6318+EPSG:5866", "EPSG:26917+EPSG:5866"]
    steps = ["EPSG:32617+EPSG:5866", "EPSG:9755", "EPSG:6318", "EPSG:26917+EPSG:5866"]
    tf = Transformer(crs_from=crs_from, crs_to=crs_to, steps=steps)
    ############ raster transformation ##############
    # index, zt = subgrid_raster_transform(fname=fname,
    #                                      rasters_dir="./sub_grids/",
    #                                     #  rasters_dir="/vsimem/sub_grids/",
    #                                      tf=tf
    #                                      )


    ############ point transformation ##############
    index, zt = subgrid_point_transform(fname, tf=tf)


    print("total time: ", time.time() - tic)
    update_vr_refinements(fname=fname, index=index, arr=zt, tf=tf)