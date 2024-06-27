import os
import pathlib
import logging
from osgeo import gdal, osr
import numpy as np
from typing import Union, Optional
import pyproj as pp
from .spatial_utils import overlapping_regions, overlapping_extents



logger = logging.getLogger("root_logger")
gdal.UseExceptions()


def band_stats(band_array: np.ndarray) -> list:
    """
    Return a list containing the min, max, mean, and std of the band array.

    Parameters
    ----------
    band_array: numpy.ndarray
        raster band array

    Returns:
    --------
    list:
        min, max, mean, and std of the band array.
    """
    return [np.nanmin(band_array), np.nanmax(band_array),
            np.nanmean(band_array), np.nanstd(band_array)]


def raster_metadata(raster_file: str, verbose: bool = False) -> dict:
    try:
        metadata = {}
        ds = gdal.Open(raster_file, gdal.GA_ReadOnly)
        srs = ds.GetSpatialRef()
        gdal_metadata = ds.GetMetadata()
        metadata |= {"description": ds.GetDescription()}
        metadata |= {"driver": ds.GetDriver().ShortName}
        metadata |= {"bands": ds.RasterCount}
        metadata |= {"dimensions": f"{ds.RasterXSize} x {ds.RasterYSize}"}
        metadata |= {"band_no_data": [ds.GetRasterBand(i+1).GetNoDataValue()
                                      for i in range(ds.RasterCount)]}
        metadata |= {"band_descriptions": [ds.GetRasterBand(i+1).GetDescription()
                                           for i in range(ds.RasterCount)]}
        # metadata |= {"band_stats": [band_stats(ds.GetRasterBand(i+1).ReadAsArray())
        #                             for i in range(ds.RasterCount)]}
        metadata |= {"compression": ds.GetMetadata("IMAGE_STRUCTURE").get("COMPRESSION", None)}
        metadata |= {"vertical_datum_wkt": gdal_metadata.get("VERTICALDATUMWKT", None)}
        metadata |= {"coordinate_epoch": srs.GetCoordinateEpoch()}
        geot = ds.GetGeoTransform()
        res_x, res_y = geot[1], geot[5]
        x_min, y_max = geot[0], geot[3]
        x_max = x_min + res_x * ds.RasterXSize
        y_min = y_max + res_y * ds.RasterYSize
        metadata |= {"geo_transform": geot}
        metadata |= {"extent": [x_min, y_min, x_max, y_max]}
        metadata |= {"resolution": [res_x, res_y]}
        metadata |= {"wkt": srs.ExportToWkt()}
        ds = None

        input_crs = pp.CRS(metadata["wkt"])
        if input_crs.is_compound:
            input_horizontal_crs = pp.CRS(input_crs.sub_crs_list[0])
            input_vertical_crs = pp.CRS(input_crs.sub_crs_list[1])
        else:
            input_horizontal_crs = input_crs
            input_vertical_crs = None

        transformer = pp.Transformer.from_crs(input_horizontal_crs,
                                              "EPSG:6318",
                                              always_xy=True
                                              )
        [[lon_min, lon_max], [lat_min, lat_max]] = transformer.transform([x_min, x_max],
                                                                         [y_min, y_max])
        metadata |= {"geo_extent": [lon_min, lat_min, lon_max, lat_max]}
        metadata |= {"overlapping_regions": overlapping_regions(r"C:\Users\mohammad.ashkezari\Desktop\vdatum_all_20230907\vdatum",
                                                                *metadata["geo_extent"])}
        metadata |= {"overlapping_extents": overlapping_extents(*metadata["geo_extent"])}
        metadata |= {"info": gdal.Info(raster_file, format="json")}

    except Exception as e:
        logger.exception(f"Unable to get raster metadata: {e}")

    if verbose:
        print(f"{'-'*80}\nFile: {pathlib.Path(raster_file).name}"
              f"\n\tInput CRS: {input_crs.name}"
              f"\n\tInput Horizontal Authority: {input_horizontal_crs.to_authority()}"
              f"\n\tInput Vertical Authority: {input_vertical_crs.to_authority() if input_crs.is_compound else None}"
              f"\n\tInput Vertical CRS: {input_vertical_crs if input_crs.is_compound else None}"
              f"\n\tInput Vertical CRS WKT: {input_vertical_crs.to_wkt() if input_crs.is_compound else None}"
              f"\n\tInput Vertical Datum WKT (Xipe): {metadata['vertical_datum_wkt']}"
              f"\n{'-'*80}\n"
              )
    return metadata


def add_overview(raster_file: str, embedded: bool = True, compression: str = "") -> None:
    """
    Add overview bands to a raster file with no existing overviews.

    parameters
    ----------
    raster_file: str
        Absolute full path to the raster file.
    embedded: bool, default=True
        If True, the overviews will be embedded in the file, otherwise stored externally.
    compression: str
        The name of compression algorithm.
    """
    try:
        if embedded:
            ds = gdal.Open(raster_file, gdal.GA_Update)
        else:
            ds = gdal.Open(raster_file, gdal.GA_ReadOnly)
        if compression:
            gdal.SetConfigOption("COMPRESS_OVERVIEW", compression)
    finally:
        ds.BuildOverviews("NEAREST", [2, 4, 8, 16, 32], gdal.TermProgress_nocb)
        ds = None
    return


def add_rat(raster: str) -> None:
    """
    Add Raster Attribute Table (RAT) to all bands of a raster file.

    parameters
    ----------
    raster_file: str
        Absolute full path to the raster file.
    """
    ds = gdal.Open(raster)
    for i in range(ds.RasterCount):
        rat = gdal.RasterAttributeTable()
        rat.CreateColumn("VALUE", gdal.GFT_Real, gdal.GFU_Generic)
        rat.CreateColumn("COUNT", gdal.GFT_Integer, gdal.GFU_Generic)
        band = ds.GetRasterBand(i+1)
        unique, counts = np.unique(band.ReadAsArray(), return_counts=True)
        for i in range(len(unique)):
            rat.SetValueAsDouble(i, 0, float(unique[i]))
            rat.SetValueAsInt(i, 1, int(counts[i]))
        band.SetDefaultRAT(rat)
    ds = None
    return


def set_nodatavalue(raster_file: str,
                    band_nodatavalue: Union[list[tuple[int, float]], float],
                    ) -> None:
    """
    Change the NoDataValue of the raster file bands.

    parameters
    ----------
    raster_file: str
        Absolute full path to the raster file.
    band_nodatavalue: Union[list[tuple[int, float]], float]
        A list of tuples: (band_index, NoDataValue).
        If a single float is passed, all bands will be affected.
    """
    if isinstance(band_nodatavalue, float):
        ds = gdal.Open(raster_file)
        band_nodatavalue = [(b, band_nodatavalue) for b in range(1, ds.RasterCount+1)]
        ds = None
    ds = gdal.Open(raster_file, gdal.GA_Update)
    for b, nodv in band_nodatavalue:
        band = ds.GetRasterBand(b)
        bar = band.ReadAsArray()
        bar[np.where(bar == band.GetNoDataValue())] = nodv
        band.WriteArray(bar)
        ds.GetRasterBand(b).SetNoDataValue(nodv)
        band = None
    ds = None
    return


def raster_compress(raster_file_path: str,
                    output_file_path: str,
                    format: str,
                    compression: str
                    ):
    """
    Compress raster file.

    Parameters
    ----------
    raster_file_path: str
        absolute path to the input raster file.
    output_file_path: str
        absolute path to the compressed output raster file.
    format: str
        raster file format.
    compression: str
        compression algorithm.
    """
    translate_kwargs = {"format": format,
                        "creationOptions": [f"COMPRESS={compression}",
                                            "BIGTIFF=IF_NEEDED",
                                            "TILED=YES"
                                            ]
                        }
    gdal.Translate(output_file_path, raster_file_path, **translate_kwargs)
    return

def crs_to_code_auth(crs: pp.CRS) -> Optional[str]:
    """
    Return CRS string representation in form of code:authority

    Raises
    -------
    ValueError:
        If either code of authority of the crs (or its sub_crs) can not be determined.

    Returns
    --------
    str:
        crs string in form of code:authority
    """
    def get_code_auth(_crs: pp.CRS):
        if _crs.to_authority(min_confidence=100):
            return ":".join(_crs.to_authority(min_confidence=100))
        raise ValueError(f"Unable to produce authority name and code for this crs:\n{_crs}")

    if crs.is_compound:
        hcrs = pp.CRS(crs.sub_crs_list[0])
        vcrs = pp.CRS(crs.sub_crs_list[1])
        code_auth = f"{get_code_auth(hcrs)}+{get_code_auth(vcrs)}"
    else:
        code_auth = get_code_auth(crs)
    return code_auth


def warp(input_file: str,
         output_file: str,
         apply_vertical: bool,
         crs_from: Union[pp.CRS, str],
         crs_to: Union[pp.CRS, str],
         input_metadata: dict,
         warp_kwargs: Optional[dict] = None
         ):
    """
    A gdal-warp wrapper to transform an NBS raster (GTiff) file with 3 bands:
    Elevation, Uncertainty, and Contributors.

    Parameters
    ----------
    input_file: str
        Path to the input raster file (gdal supported).
    output_file: str
        Path to the transformed raster file.
    apply_vertical: bool
        Apply GDAL vertical shift.
    crs_from: pyproj.crs.CRS or input used to create one
        Projection of input data.
    crs_to: pyproj.crs.CRS or input used to create one
        Projection of output data.
    input_metadata: dict
        Dictionary containing metadata generated by vyperdatum.raster_utils.raster_metadata()
    warp_kwargs: dict
        gdal kwargs.

    Returns
    --------
    str:
        Absolute path to the transformed file.
    """
    if isinstance(crs_from, pp.CRS):
        crs_from = crs_to_code_auth(crs_from)
    if isinstance(crs_to, pp.CRS):
        crs_to = crs_to_code_auth(crs_to)

    gdal.Warp(output_file,
              input_file,
              dstSRS=crs_to,
              srcSRS=crs_from,
              # xRes=input_metadata["resolution"][0],
              # yRes=abs(input_metadata["resolution"][1]),
              # outputBounds=input_metadata["extent"],
              **(warp_kwargs or {})
              )

    if apply_vertical:
        # horizontal CRS MUST be identical for both source and target
        if isinstance(warp_kwargs.get("srcBands"), list):
            ds_in = gdal.Open(input_file, gdal.GA_ReadOnly)
            ds_out = gdal.Open(output_file, gdal.GA_ReadOnly)
            # combine the vertically transformed bands and
            # the non-transformed ones into a new raster
            driver = gdal.GetDriverByName(input_metadata["driver"])
            mem_path = f"/vsimem/{os.path.splitext(os.path.basename(output_file))[0]}.tiff"
            ds_temp = driver.Create(mem_path,
                                    ds_in.RasterXSize,
                                    ds_in.RasterYSize,
                                    ds_in.RasterCount,
                                    gdal.GDT_Float32
                                    )
            ds_temp.SetGeoTransform(ds_out.GetGeoTransform())
            ds_temp.SetProjection(ds_out.GetProjection())
            for b in range(1, ds_in.RasterCount+1):
                if b in warp_kwargs.get("srcBands"):
                    out_shape = ds_out.GetRasterBand(b).ReadAsArray().shape
                    in_shape = ds_in.GetRasterBand(b).ReadAsArray().shape
                    if out_shape != in_shape:
                        logger.error(f"Band {b} dimensions has changed from"
                                     f"{in_shape} to {out_shape}")
                    ds_temp.GetRasterBand(b).WriteArray(ds_out.GetRasterBand(b).ReadAsArray())
                    ds_temp.GetRasterBand(b).SetDescription(ds_out.GetRasterBand(b).GetDescription())
                    ds_temp.GetRasterBand(b).SetNoDataValue(ds_out.GetRasterBand(b).GetNoDataValue())
                else:
                    ds_temp.GetRasterBand(b).WriteArray(ds_in.GetRasterBand(b).ReadAsArray())
                    ds_temp.GetRasterBand(b).SetDescription(ds_in.GetRasterBand(b).GetDescription())
                    ds_temp.GetRasterBand(b).SetNoDataValue(ds_in.GetRasterBand(b).GetNoDataValue())
            ds_in, ds_out = None, None
            ds_temp.FlushCache()
            driver.CreateCopy(output_file, ds_temp)
            ds_temp = None
            gdal.Unlink(mem_path)

    if input_metadata["compression"]:
        output_file_copy = str(output_file)+".tmp"
        os.rename(output_file, output_file_copy)
        raster_compress(output_file_copy, output_file,
                        input_metadata["driver"], input_metadata['compression']
                        )
        os.remove(output_file_copy)
    return output_file


def post_transformation_checks(source_file: str,
                               target_file: str,
                               target_crs: Union[pp.CRS, str],
                               ):
    """
    Run a number of sanity checks on the transformed raster file.
    Warns if a check fails.

    Parameters
    ----------
    source_file: str
        Absolute path to the input raster file.
    target_file: str
        Absolute path to the target raster file.
    target_crs:  pyproj.crs.CRS or input used to create one
        The expected CRS object for the target raster file.

    Returns
    ----------
    bool
        Returns True if all checks pass, otherwise False.
    """
    if ~isinstance(target_crs, pp.CRS):
        target_crs = pp.CRS(target_crs)
    source_meta = raster_metadata(source_file)
    target_meta = raster_metadata(target_file)
    passed = True
    target_auth = target_crs.to_authority()
    transformed_auth = pp.CRS(target_meta["wkt"]).to_authority()
    if target_auth != transformed_auth:
        passed = False
        logger.warning(">>>>> Warning <<<<< The expected authority code/name of the "
                       f"transformed raster is {target_auth}, but received {transformed_auth}"
                       )
    if source_meta["bands"] != target_meta["bands"]:
        passed = False
        logger.warning(">>>>> Warning <<<<< Number of bands in the source file "
                       f"({source_meta['bands']}) doesn't match target ({target_meta['bands']}).")
    if source_meta["dimensions"] != target_meta["dimensions"]:
        passed = False
        logger.warning(">>>>> Warning <<<<< The source file band dimensions "
                       f" ({source_meta['dimensions']}) don't match those of the "
                       f"transformed file ({target_meta['dimensions']}).")
    if source_meta["resolution"][0] != target_meta["resolution"][0] or source_meta["resolution"][1] != target_meta["resolution"][1]:
        passed = False
        logger.warning(">>>>> Warning <<<<< The source file pixel size "
                       f" ({source_meta['resolution']}) don't match those of the "
                       f"transformed file ({target_meta['resolution']}).")
    return passed
