from vyperdatum.transformer import Transformer


crs_from = "EPSG:6347"
crs_to = "EPSG:6347+NOAA:98"

input_file = r"C:\Users\mohammad.ashkezari\Desktop\Fuse_Test\raster\Original\nc\NC1901-TB-C_BLK-03_US4NC1AC_ellipsoidal_dem.tif"
tf = Transformer(crs_from=crs_from,
                 crs_to=crs_to,
                 )
output_file = input_file.replace("Original", "Manual")
tf.transform_raster(input_file=input_file,
                    output_file=output_file,
                    overview=False,
                    pre_post_checks=True,
                    vdatum_check=True
                    )