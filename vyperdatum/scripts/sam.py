from vyperdatum.transformer import Transformer


Transformer(crs_from="EPSG:6338+EPSG:5703",
            crs_to="EPSG:6338+NOAA:98",
            ).transform_raster(input_file=r"C:\Users\mohammad.ashkezari\Desktop\Example NWLD Transforms\Alaska\input.tif",
                               output_file=r"C:\Users\mohammad.ashkezari\Desktop\Example NWLD Transforms\Alaska\output.tif",
                               overview=False,
                               pre_post_checks=False,
                               vdatum_check=False
                               )


Transformer(crs_from="EPSG:6347",
            crs_to="EPSG:6347+NOAA:98",
            ).transform_raster(input_file=r"C:\Users\mohammad.ashkezari\Desktop\Example NWLD Transforms\NC\input.tif",
                               output_file=r"C:\Users\mohammad.ashkezari\Desktop\Example NWLD Transforms\NC\output.tif",
                               overview=False,
                               pre_post_checks=False,
                               vdatum_check=False
                               )
