import os
import shutil
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
        x_min, y_max = geot[0], geot[3]
        x_max = x_min + geot[1] * ds.RasterXSize
        y_min = y_max + geot[5] * ds.RasterYSize
        metadata |= {"geo_transform": geot}
        metadata |= {"extent": [x_min, y_min, x_max, y_max]}
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
         driver: str,
         compression: str,
         from_epoch: Optional[float] = None,
         to_epoch:  Optional[float] = None
         ) -> None:
    """
    Transform an NBS raster (GTiff) file with 3 bands: Elevation, Uncertainty, and Contributors.

    TODO: unfinished implementation/doc
    """
    if isinstance(crs_from, pp.CRS):
        crs_from = crs_to_code_auth(crs_from)
    if isinstance(crs_to, pp.CRS):
        crs_to = crs_to_code_auth(crs_to)
    options = []
    if from_epoch is not None:
        options += [f"s_coord_epoch={from_epoch}"]
    if to_epoch is not None:
        options += [f"t_coord_epoch={to_epoch}"]
    print(f"Generating: {output_file}")
    try:
        tmp_output_file = shutil.copy2(input_file, str(output_file)+".tmp")
        translate_kwargs = {"format": driver,
                            "creationOptions": [f"COMPRESS={compression}",
                                                "BIGTIFF=IF_NEEDED",
                                                "TILED=YES"
                                                ]
                            }
        if apply_vertical:
            kwargs = {
                "srcBands": [1],
                "dstBands": [1],
                "warpOptions": ["APPLY_VERTICAL_SHIFT=YES"],
                "srcSRS": crs_from,
                "dstSRS": crs_to,
                "errorThreshold": 0,
                }
            ds_out = gdal.Open(tmp_output_file, gdal.GA_Update)
            gdal.Warp(ds_out, input_file, **kwargs)
            del ds_out
            ds = gdal.Translate(output_file, tmp_output_file, **translate_kwargs)
            sref = osr.SpatialReference()
            sref.SetFromUserInput(crs_to)
            ds.SetSpatialRef(sref)
            del ds
        else:
            hcrs_from, hcrs_to = [crs.split("+")[0] for crs in (crs_from, crs_to)]
            vcrs_from, vcrs_to = [(crs.split("+")[-1] if "+" in crs else None) for crs in (crs_from, crs_to)]
            if vcrs_from is not None and vcrs_to is not None:
                assert vcrs_from == vcrs_to
                crs_out = crs_to
            elif vcrs_from is None and vcrs_to is None:
                crs_out = crs_to
            else:
                crs_out = f"{hcrs_to}+{vcrs_from}" if vcrs_from else f"{hcrs_to}+{vcrs_to}"

            kwargs = {
                "format": "vrt",
                "outputType": gdal.gdalconst.GDT_Float32,
                "srcSRS": hcrs_from,
                "dstSRS": hcrs_to,
                "options": options,
                "warpOptions": ["APPLY_VERTICAL_SHIFT=NO"],
                }
            gdal.Warp(tmp_output_file, input_file, **kwargs)
            ds = gdal.Translate(output_file, tmp_output_file, **translate_kwargs)
            sref = osr.SpatialReference()
            sref.SetFromUserInput(crs_out)
            ds.SetSpatialRef(sref)
            del ds
    finally:
        if os.path.isfile(tmp_output_file):
            os.remove(tmp_output_file)
    return


def gdal_warp(input_file: str,
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
    if warp_kwargs:
        gdal.Warp(output_file,
                  input_file,
                  dstSRS=crs_to,
                  srcSRS=crs_from,
                  **warp_kwargs
                  )
    else:
        gdal.Warp(output_file,
                  input_file,
                  dstSRS=crs_to,
                  srcSRS=crs_from
                  )

    if apply_vertical:
        # horizontal CRS MUST be identical for both source and target
        if isinstance(warp_kwargs.get("srcBands"), list):
            ds_in = gdal.Open(input_file, gdal.GA_ReadOnly)
            ds_out = gdal.Open(output_file, gdal.GA_ReadOnly)
            # combine the vertically transformed bands and
            # the non-transformed ones into a new file raster
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
