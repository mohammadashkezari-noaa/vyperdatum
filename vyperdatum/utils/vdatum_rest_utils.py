
import requests
import logging
import numpy as np
from osgeo import gdal
from typing import Optional
import pyproj as pp

logger = logging.getLogger("root_logger")
gdal.UseExceptions()


def vdatum_transform_point(s_x, s_y, s_z, region,
                           s_h_frame, s_v_frame,
                           t_h_frame, t_v_frame,
                           s_v_goid="geoid18",
                           t_v_goid="geoid18",
                           ):
    """
    Call point transformation GET endpoint (/convert) of the Vdatum REST API.
    API docs: https://vdatum.noaa.gov/docs/services.html

    Parameters
    ----------
    s_x: float
        Source point longitude
    s_y: float
        Source point latitude
    s_z: float
        Source point height
    region: str
        Vdatum region name (e.g. ak, as, contiguous, gcnmi, prvi)
        https://vdatum.noaa.gov/docs/services.html#step140.
    s_h_frame: str
        Source horizontal reference frame (e.g. NAD83_2011)
        https://vdatum.noaa.gov/docs/services.html#step150
    s_v_frame: str
        source vertical reference frame (e.g. NAVD88, PRVD02, MLLW)
        https://vdatum.noaa.gov/docs/services.html#step160
    t_h_frame: str
        Input target horizontal reference frame (e.g. NAD83_2011)
        https://vdatum.noaa.gov/docs/services.html#step150
    t_v_frame: str
        Input target vertical reference frame (e.g. NAVD88, PRVD02, MLLW)
        https://vdatum.noaa.gov/docs/services.html#step160
    s_v_goid: str
        Source vertical GEOID model (e.g. geoid18 (default), geoid12b,
        geoid12a, geoid09, geoid06, geoid03, geoid99, geoid96, egm2008,
        egm1996, egm1984, xgeoid16b, xgeoid17b, xgeoid18b, xgeoid19b,
        xgeoid20b)
    t_v_goid: str
        Target vertical GEOID model (e.g. geoid18 (default), geoid12b,
        geoid12a, geoid09, geoid06, geoid03, geoid99, geoid96, egm2008,
        egm1996, egm1984, xgeoid16b, xgeoid17b, xgeoid18b, xgeoid19b,
        xgeoid20b)

    Returns
    -------
    Optional[tuple]
        The transformed coordinates (lon, lat, height)
    Optional[dict]
        The complete vdatum response object
    """
    url = "https://vdatum.noaa.gov/vdatumweb/api/convert"
    params = dict(s_x=s_x, s_y=s_y, s_z=s_z, region=region,
                  s_h_frame=s_h_frame, s_v_frame=s_v_frame,
                  t_h_frame=t_h_frame, t_v_frame=t_v_frame,
                  s_v_goid=s_v_goid, t_v_goid=t_v_goid)
    try:
        resp = requests.get(url, params=params, timeout=200).json()
    except Exception as e:
        logger.exception(f"VDatum API exception:\n{e}")
        return None, None
    return (float(resp.get("t_x", np.nan)),
            float(resp.get("t_y", np.nan)),
            float(resp.get("t_z", np.nan))), resp


def api_region_alias(region: str):
    """
    Vdatum REST api uses different region names compared to those
    listed in the vdatum grids directory. This function expects to
    receive region name according to the vdatum grids directory and
    returns region name consistent with the vdatum REST api. Default
    output is `contiguous`.

    Parameters
    ------------
    region: str
         Region name according to the vdatum grids directory.

    Returns
    ------------
    str
    """
    api_region = "contiguous"
    if region.startswith("AK"):
        api_region = "ak"
    elif region.startswith("WA") or region.startswith("OR") or region.startswith("WC"):
        api_region = "westcoast"
    elif region.startswith("PRVI"):
        api_region = "prvi"
    # Note: not all regions are covered here. For example, I do'nt know what is the Hawaii
    # region name in vdatum grid directory (or as, sgi, spi, sli, gcnmi, wgom, ...).
    # why `westcoast` and `chesapeak_delaware` are not considered as part of `contiguous`?.
    # Needs input from others.
    # https://vdatum.noaa.gov/docs/services.html#step140
    return api_region


def wkt_to_crs(wkt: str) -> tuple[Optional[str], Optional[str]]:
    """
    Receives WKT and returns the horizontal/vertical CRS names.

    Parameters
    ------------
    wkt: str
         WKT string.

    Returns
    ------------
    tuple[Optional[str], Optional[str]]
         Horizontal and vertical CRS names, if identified.
    """
    input_crs = pp.CRS(wkt)
    if input_crs.is_compound:
        horizontal_crs = pp.CRS(input_crs.sub_crs_list[0])
        vertical_crs = pp.CRS(input_crs.sub_crs_list[1])
    else:
        horizontal_crs = input_crs
        vertical_crs = None
    return horizontal_crs.name, vertical_crs.name if vertical_crs else None


def api_crs_alias(wkt: str):
    """
    Vdatum REST api uses different CRS names compared to those
    of the PROJ/pyproj. This function expects to receive a CRS WKT
    and returns a CRS name that is consumable by the vdatum REST api.

    Parameters
    ------------
    wkt: str
         WKT string.

    Returns
    ------------
    str
        CRS name that is consumable by the vdatum REST api.
    """
    # h_crs, v_crs = wkt_to_crs(wkt)
    raise NotImplementedError("""The api crs naming are quite arbitrary and doesn't have
                              documentation on how to handle different projected crs such as 
                              MTM, BLM, MTQ, UTM, ... (I queried database to get some of the 
                              existing projections). I don't think we can robustly implement
                              this function. Will come back to if found a solution. For now
                              I will transform the sampled points from both source and target
                              to a common horizontal crs such as NAD83(2011).""")
    return


def index_to_xy(i: int, j: int, geot: tuple):
    """
    Take indices of a raster's band array and return x, y.

    Parameters
    ----------
    i: int
        Raster's band array first index.
    j: int
        Raster's band array second index.
    geot: tuple
        Gdal GeoTransform tuple object.

    Returns
    ----------
    float, float
        easting, northing
    """
    res_x, res_y = geot[1], geot[5]
    x_min, y_max = geot[0], geot[3]
    x = i * res_x + x_min + (res_x / 2)
    y = j * res_y + y_max + (res_y / 2)
    return x, y


def sample_raster(source_meta: dict,
                  target_meta: dict,
                  n_sample: int,
                  sampling_band: int = 1,
                  common_h_crs: Optional[str] = None
                  ):
    """
    Randomly draw `n_samples` points (not NoDataValue) from the `sampling_band`
    of the source and target rasters.

    Parameters
    ----------
    source_meta: dict
        Source raster metadata generated by `raster_metadata` function.
    target_meta: dict
        Target raster metadata generated by `raster_metadata` function.
    n_sample: int
        The number of sample points (coordinates).
    sampling_band: dict
        The index of the source band to be sampled (default 1).
    common_h_crs: Optional[str]
        When not None, both source and target samples are transformed
        into a common horizontal CRS, otherwise ignored (default None).

    Raises
    -------
    ValueError:
        If there are less not-null values than `n_sample` in the target raster band.

    Returns
    ----------
    bool
        Returns `n_samples` points from the rasters in form of two lists of [x, y, value].
    """
    ds_source = gdal.Open(source_meta["path"])
    ds_target = gdal.Open(target_meta["path"])
    bar_source = ds_source.GetRasterBand(sampling_band).ReadAsArray()
    bar_target = ds_target.GetRasterBand(sampling_band).ReadAsArray()
    nodata_value = ds_target.GetRasterBand(sampling_band).GetNoDataValue()
    if np.count_nonzero(np.where(bar_target != nodata_value)) < n_sample:
        raise ValueError(f"Cannot sample {n_sample} from the target raster. Too many NoDataValue.")
    source_samples, target_samples = [], []
    c = 0
    while len(target_samples) < n_sample:
        c += 1
        if c > 1e6:
            raise ValueError(f"Failed to find {n_sample} sample points from the target raster.")
        i, j = np.random.choice(bar_target.shape[0]), np.random.choice(bar_target.shape[1])
        if bar_target[i, j] == nodata_value:
            continue
        x, y = index_to_xy(i, j, ds_target.GetGeoTransform())
        target_samples.append([x, y, bar_target[i, j]])
        source_i = int(bar_source.shape[0] * i / bar_target.shape[0])
        source_j = int(bar_source.shape[1] * j / bar_target.shape[1])
        source_x, source_y = index_to_xy(source_i, source_j, ds_source.GetGeoTransform())
        source_samples.append([source_x, source_y, bar_source[source_i, source_j]])
    ds_source, ds_target = None, None
    if common_h_crs:
        source_crs_h, _ = wkt_to_crs(source_meta["wkt"])
        target_crs_h, _ = wkt_to_crs(target_meta["wkt"])
        source_transformer = pp.Transformer.from_crs(pp.CRS(source_crs_h),
                                                     pp.CRS(common_h_crs),
                                                     always_xy=True
                                                     )
        target_transformer = pp.Transformer.from_crs(pp.CRS(target_crs_h),
                                                     pp.CRS(common_h_crs),
                                                     always_xy=True
                                                     )
    return source_samples, target_samples


def vdatum_raster_cross_validate(source_meta: dict,
                                 target_meta: dict,
                                 n_sample: int,
                                 sampling_band: int = 1,
                                 region: Optional[str] = None,
                                 s_h_frame: Optional[str] = None,
                                 s_v_frame: Optional[str] = None,
                                 t_h_frame: Optional[str] = None,
                                 t_v_frame: Optional[str] = None
                                 ):
    """
    Randomly sample the source raster points and transform them to the
    target CRS using the vdatum API. Verify if the transformed values are
    consistent with the target raster values.

    Parameters
    ----------
    source_meta: dict
        Source raster metadata generated by `raster_metadata` function.
    target_meta: dict
        Target raster metadata generated by `raster_metadata` function.
    n_sample: int
        The number of sample points (coordinates).
    sampling_band: dict
        The index of the source band to be sampled (default 1).

    Returns
    ----------
    bool
        Returns True if all checks pass, otherwise False.
    """
    passed = True
    if not region:
        region = "contiguous"
        if len(source_meta["overlapping_regions"]) != 1:
            passed = False
            logger.warning(">>>>> Warning <<<<< The raster is not overlapping with a single region. "
                           f"The overlapping regions: ({source_meta['overlapping_regions']}).")
        else:
            region = api_region_alias(source_meta["overlapping_regions"][0])

    source_crs_h, source_crs_v = wkt_to_crs(source_meta["wkt"])
    target_crs_h, target_crs_v = wkt_to_crs(target_meta["wkt"])
    if source_crs_h != target_crs_h:
        passed = False
        logger.warning(">>>>> Warning <<<<< The source and target horizontal CRS don't match. "
                       f"\n\tSource horizontal crs: {source_crs_h}."
                       f"\n\tTarget horizontal crs: {target_crs_h}.")

    source_samples, target_samples = sample_raster(source_meta, target_meta,
                                                   n_sample, sampling_band)


    # points, resp = vdatum_transform_point(s_x=xx, s_y=yy, s_z=zz, region=region,
    #                                       s_h_frame="NAD83_2011", s_v_frame="MLLW",
    #                                       t_h_frame="NAD83_2011", t_v_frame="NAVD88")
    

    # target_auth = target_crs.to_authority()
    # transformed_auth = pp.CRS(target_meta["wkt"]).to_authority()
    # if target_auth != transformed_auth:
    #     passed = False
    #     logger.warning(">>>>> Warning <<<<< The expected authority code/name of the "
    #                    f"transformed raster is {target_auth}, but received {transformed_auth}"
    #                    )

    return passed


if __name__ == "__main__":
    # expected output
    tx, ty, tz = -70.7, 43, -1.547
    # input values
    xx, yy, zz = -70.7, 43, 0

    points, resp = vdatum_transform_point(s_x=xx, s_y=yy, s_z=zz, region="contiguous",
                                          s_h_frame="NAD83_2011", s_v_frame="MLLW",
                                          t_h_frame="NAD83_2011", t_v_frame="NAVD88")
    print("output:", points)
    print("expected:", (tx, ty, tz))


    # # example for out-of-bound point; below is the vdatum response
    # # {'errorCode': 412, 'message': 'Uncaught error, please contact NOAA VDatum Program Support team.'}
    # result = vdatum_transform_point(s_x=xx, s_y=yy, s_z=zz, region="chesapeak_delaware",
    #                                 s_h_frame="NAD83_2011", s_v_frame="NAD83_2011",
    #                                 t_h_frame="NAD83_2011", t_v_frame="NAVD88")
    # print("output:", result)
    # print("expected:", (tx, ty, tz))
