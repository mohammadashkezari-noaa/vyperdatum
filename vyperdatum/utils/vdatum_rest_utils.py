
import requests
import logging
import numpy as np
from osgeo import gdal
from typing import Optional
import pyproj as pp
import difflib
from vyperdatum.enums import VDATUM


logger = logging.getLogger("root_logger")
gdal.UseExceptions()


def vdatum_transform_point(s_x, s_y, s_z, region,
                           s_h_frame, s_v_frame, s_h_zone,
                           t_h_frame, t_v_frame, t_h_zone,
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
                  s_h_zone=s_h_zone if s_h_zone else "",
                  t_h_frame=t_h_frame, t_v_frame=t_v_frame,
                  t_h_zone=t_h_zone if t_h_zone else "",
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


def wkt_to_utm(wkt: str) -> Optional[str]:
    """
    Receives WKT and returns the UTM zone, if applicable.

    Parameters
    ------------
    wkt: str
         WKT string

    Returns
    ------------
    Optional[str]
         UTM zone
    """
    zone = None
    input_crs = pp.CRS(wkt)
    if not input_crs.is_projected:
        return zone
    input_crs = input_crs.name.split("+")[0].strip()
    if len(input_crs.split("/ UTM zone ")) == 2:
        zone = input_crs.split("/ UTM zone ")[1].strip()
    return zone


def wkt_to_crs(wkt: str) -> tuple[Optional[str], Optional[str]]:
    """
    Receives WKT and returns the horizontal/vertical CRS names.

    Parameters
    ------------
    wkt: str
         WKT string

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


def api_crs_aliases(wkt: str) -> tuple[str, str]:
    """
    Vdatum REST api uses different CRS names compared to those
    of the PROJ/pyproj. This function expects to receive a CRS WKT
    and returns horizontal and vertical CRS names that are consumable
    by the vdatum REST api.

    Raises
    ------------
    ValueError
         When the standard CRS name can't be matched with any Vdatum API CRS names.

    Parameters
    ------------
    wkt: str
         WKT string.

    Returns
    ------------
    tuple[str, str]
        Horizontal and vertical CRS names that are consumable by the vdatum REST api.
    """
    h_crs, v_crs = wkt_to_crs(wkt)
    h_crs = h_crs.split("/")[0].strip()
    h_matches = difflib.get_close_matches(h_crs, VDATUM.H_FRAMES.value)
    if len(h_matches) == 0:
        raise ValueError(f"No Vdatum horizontal CRS name matched with '{h_crs}'")
    h_crs = h_matches[0]

    v_crs_black = ["HRD"]
    if v_crs and v_crs.split()[0].upper().strip() in v_crs_black:
        raise ValueError(f"The raster's vertical CRS is '{v_crs}' which is not covered by Vdatum.")

    if not v_crs:
        v_crs = h_crs
    else:
        v_matches = difflib.get_close_matches(v_crs, VDATUM.V_FRAMES.value)
        if len(v_matches) == 0:            
            v_matches = difflib.get_close_matches(v_crs.split()[0].strip(), VDATUM.V_FRAMES.value)
        if len(v_matches) == 0:
            v_matches = difflib.get_close_matches(v_crs.split()[0].strip(), VDATUM.V_FRAMES.value)
            raise ValueError(f"No Vdatum vertical CRS name matched with '{v_crs}'")
        v_crs = v_matches[0]
    return h_crs, v_crs


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
                  sampling_band: int,
                  common_h_crs: Optional[str]
                  ) -> tuple[list, list]:
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
        Example: common_h_crs = 'EPSG:6318'

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
        for i, p in enumerate(source_samples):
            lon, lat = source_transformer.transform(p[0], p[1])
            p[0], p[1] = lon, lat
            lon, lat = target_transformer.transform(target_samples[i][0], target_samples[i][1])
            target_samples[i][0], target_samples[i][1] = lon, lat
    return source_samples, target_samples


def vdatum_raster_cross_validate(source_meta: dict,
                                 target_meta: dict,
                                 n_sample: int,
                                 sampling_band: int = 1,
                                 region: Optional[str] = None,
                                 s_h_frame: Optional[str] = None,
                                 s_v_frame: Optional[str] = None,
                                 s_h_zone: Optional[str] = None,
                                 t_h_frame: Optional[str] = None,
                                 t_v_frame: Optional[str] = None,
                                 t_h_zone: Optional[str] = None
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
            # passed = False
            logger.warning(">>>>> Warning <<<<< The input is not overlapping with a single region."
                           f" The overlapping regions: ({source_meta['overlapping_regions']}).")
        else:
            region = api_region_alias(source_meta["overlapping_regions"][0])

    source_crs_h, source_crs_v = wkt_to_crs(source_meta["wkt"])
    source_zone_h = wkt_to_utm(source_meta["wkt"])
    target_crs_h, target_crs_v = wkt_to_crs(target_meta["wkt"])
    target_zone_h = wkt_to_utm(target_meta["wkt"])

    # if source_crs_h != target_crs_h:
    #     passed = False
    #     logger.warning(">>>>> Warning <<<<< The source and target horizontal CRS don't match. "
    #                    f"\n\tSource horizontal crs: {source_crs_h}."
    #                    f"\n\tTarget horizontal crs: {target_crs_h}.")

    if not (s_h_frame and s_v_frame):
        source_crs_h, source_crs_v = api_crs_aliases(source_meta["wkt"])
    if not (t_h_frame and t_v_frame):
        target_crs_h, target_crs_v = api_crs_aliases(target_meta["wkt"])

    source_samples, target_samples = sample_raster(source_meta, target_meta,
                                                   n_sample, sampling_band,
                                                   common_h_crs=None)

    for i, p in enumerate(source_samples):
        points, resp = vdatum_transform_point(s_x=p[0], s_y=p[1], s_z=p[2],
                                              region=region,
                                              s_h_frame=s_h_frame or source_crs_h,
                                              s_v_frame=s_v_frame or source_crs_v,
                                              s_h_zone=s_h_zone or source_zone_h,
                                              t_h_frame=t_h_frame or target_crs_h,
                                              t_v_frame=t_v_frame or target_crs_v,
                                              t_h_zone=t_h_zone or target_zone_h)
        print(f"""Source: ({p[0], p[1], p[2]})
            Target: ({target_samples[i][0], target_samples[i][1], target_samples[i][2]})
            Vdatum: ({points[0], points[1], points[2]})""")
        print(">>>>>>>>>>>>")
        print(resp)

    return passed


if __name__ == "__main__":
    from vyperdatum.utils.raster_utils import raster_metadata
    import sys

    input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\NVD\VA_input.tif"
    input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\NVD\_transformed_VA_input.tif"

    input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\PBC\clipped_MA2204-TB-N_TPU_3band_mosaic_tpu.tif"
    input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\PBC\_03_clipped_MA2204-TB-N_TPU_3band_mosaic_tpu.tif"

    # FAILS: VDATUM DOESNOT HAVE HRD ... WILL BE MIXED WITH HRD  ... ALSO CHECK WGS84_G873 
    input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\HRD\Tile1_PBC18_4m_20211001_145447.tif"
    # input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\HRD\_03_6318_5703_Tile1_PBC18_4m_20211001_145447.tif"

    # input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\BlueTopo\BC25L26L\Modeling_BC25L26L_20230919.tiff"
    # input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\BlueTopo\BC25L26L\_03_6318_5703_Modeling_BC25L26L_20230919.tiff"

    # input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\PRVD\PBG19\Modeling_BC26H26C_20240304_20240501190016\Modeling_BC26H26C_20240304.tiff"

    # meta = raster_metadata(input_file, verbose=True)
    # print(api_crs_aliases(meta["wkt"]))


    s_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\PBC\clipped_MA2204-TB-N_TPU_3band_mosaic_tpu.tif"
    t_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\PBC\_03_clipped_MA2204-TB-N_TPU_3band_mosaic_tpu.tif"

    vdatum_raster_cross_validate(source_meta=raster_metadata(s_file),
                                 target_meta=raster_metadata(t_file),
                                 n_sample=1,
                                 sampling_band=1,
                                 region=None,
                                 s_h_frame=None,
                                 s_v_frame=None,
                                 s_h_zone=None,
                                 t_h_frame=None,
                                 t_v_frame=None,
                                 t_h_zone=None
                                 )
    sys.exit()
    ###############################################
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
