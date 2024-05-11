import pathlib
from osgeo import gdal


def warp(input_file: str,
         output_file: str,
         apply_vertical: bool,
         crs_from: str,
         crs_to: str
         ):
    kwargs = {
     "format": "GTiff",
     "srcBands": [1],
     "dstBands": [1],
     "outputType": gdal.gdalconst.GDT_Float32,
     "creationOptions": ["COMPRESS=DEFLATE"],
     "warpOptions": [f"APPLY_VERTICAL_SHIFT={'YES' if apply_vertical else 'NO'}"],
     "srcSRS": crs_from,
     "dstSRS": crs_to,
     "errorThreshold": 0,
     'options': ["s_coord_epoch=2010.0", "t_coord_epoch=2010.0"],
    }
    print(f"Generating: {output_file}")
    gdal.Warp(output_file, input_file, **kwargs)
    return


def main(input_file):
    warp(input_file=input_file,
         output_file=pathlib.Path(input_file).with_stem("_01_9755_" + pathlib.Path(input_file).stem),
         apply_vertical=False,
         crs_from="EPSG:32618",
         crs_to="EPSG:9755"
         )

    warp(input_file=pathlib.Path(input_file).with_stem("_01_9755_" + pathlib.Path(input_file).stem),
         output_file=pathlib.Path(input_file).with_stem("_02_6318_" + pathlib.Path(input_file).stem),
         apply_vertical=False,
         crs_from="EPSG:9755",
         crs_to="EPSG:6318"
         )

    warp(input_file=pathlib.Path(input_file).with_stem("_02_6318_" + pathlib.Path(input_file).stem),
         output_file=pathlib.Path(input_file).with_stem("_03_6318_5703_" + pathlib.Path(input_file).stem),
         apply_vertical=True,
         crs_from="EPSG:6318+NOAA:5503",
         crs_to="EPSG:6318+EPSG:5703"
         )
    return


if __name__ == "__main__":
    gdal.UseExceptions()
    input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\HRD\Tile1_PBC18_4m_20211001_145447.tif"
    main(input_file)
