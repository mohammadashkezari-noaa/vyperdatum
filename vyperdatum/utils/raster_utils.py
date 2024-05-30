import os
import shutil
import pathlib
import glob
import logging
from osgeo import gdal, osr
import numpy as np
from typing import Union, Optional
import pyproj as pp

logger = logging.getLogger("root_logger")
gdal.UseExceptions()


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
        metadata |= {"compression": ds.GetMetadata("IMAGE_STRUCTURE").get("COMPRESSION", None)}
        metadata |= {"vertical_datum_wkt": gdal_metadata.get("VERTICALDATUMWKT", None)}
        metadata |= {"coordinate_epoch": srs.GetCoordinateEpoch()}
        geot = ds.GetGeoTransform()
        x_min, y_max = geot[0], geot[3]
        x_max = x_min + geot[1] * ds.RasterXSize
        y_min = y_max + geot[5] * ds.RasterYSize
        metadata |= {"geo_transform": geot}
        metadata |= {"extent": [x_min, y_min, x_max, y_max]}
        sref = ds.GetSpatialRef()
        metadata |= {"wkt": sref.ExportToWkt()}
        ds = None

        input_crs = pp.CRS(metadata["wkt"])
        input_horizontal_crs = pp.CRS(input_crs.sub_crs_list[0])
        input_vertical_crs = pp.CRS(input_crs.sub_crs_list[1])

        transformer = pp.Transformer.from_crs(input_horizontal_crs,
                                              "EPSG:6318",
                                              always_xy=True
                                              )
        [[lon_min, lon_max], [lat_min, lat_max]] = transformer.transform([x_min, x_max],
                                                                        [y_min, y_max])
        metadata |= {"geo_extent": [lon_min, lat_min, lon_max, lat_max]}
    except Exception as e:
        logger.exception(f"Unable to get raster metadata: {e}")

    if verbose:
        print(f"{'-'*80}\nFile: {pathlib.Path(raster_file).name}"
              f"\n\tInput CRS: {input_crs.name}"
              f"\n\tInput Horizontal Authority: {input_horizontal_crs.to_authority()}"
              f"\n\tInput Vertical Authority: {input_vertical_crs.to_authority()}"
              f"\n\tInput Vertical CRS: {input_vertical_crs}"
              f"\n\tInput Vertical CRS WKT: {input_vertical_crs.to_wkt()}"
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


def get_region_polygons(datums_directory: str, extension: str = 'kml') -> dict:
    """"
    Search the datums directory to find all geometry files. All datums are assumed to reside in a subfolder.

    Parameters
    ----------
    datums_directory : str
        absolute folder path to the vdatum directory

    extension : str
        the geometry file extension to search for

    Returns
    -------
    dict
        dictionary of {kml name: kml path, ...}
    """

    search_path = os.path.join(datums_directory, f'*/*.{extension}')
    geom_list = glob.glob(search_path)
    if len(geom_list) == 0:
        errmsg = f'No {extension} files found in the provided directory: {datums_directory}'
        print(errmsg)
    geom = {}
    for filename in geom_list:
        geom_path, geom_file = os.path.split(filename)
        root_dir, geom_name = os.path.split(geom_path)
        geom[geom_name] = filename
    return geom