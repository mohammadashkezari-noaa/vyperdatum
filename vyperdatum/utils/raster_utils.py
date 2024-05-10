from osgeo import gdal
import numpy as np


def raster_metadata(raster_file: str) -> dict:
    metadata = {}
    ds = gdal.Open(raster_file, gdal.GA_ReadOnly)
    srs = ds.GetSpatialRef()
    metadata |= {"description": ds.GetDescription()}
    metadata |= {"driver": ds.GetDriver().ShortName}
    metadata |= {"bands": ds.RasterCount}
    metadata |= {"dimensions": f"{ds.RasterXSize} x {ds.RasterYSize}"}
    metadata |= {"band_no_data": [ds.GetRasterBand(i+1).GetNoDataValue()
                                  for i in range(ds.RasterCount)]}
    metadata |= {"band_descriptions": [ds.GetRasterBand(i+1).GetDescription()
                                       for i in range(ds.RasterCount)]}
    metadata |= {"compression": ds.GetMetadata('IMAGE_STRUCTURE').get('COMPRESSION', None)}
    metadata |= {"coordinate_epoch": srs.GetCoordinateEpoch()}
    metadata |= {"geo_transform": ds.GetGeoTransform()}
    metadata |= {"wkt": ds.GetProjection()}
    ds = None
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
