from vyperdatum.transformer import Transformer


crs_from = "EPSG:6347+EPSG:5703"
crs_to = "EPSG:6347+NOAA:98"

input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\raster\PBE\edge\Original\usace2018_post_florence_dem_J1138068_008_004.tif"
tf = Transformer(crs_from=crs_from,
                 crs_to=crs_to,
                 )
output_file = input_file.replace("Original", "Manual")
tf.transform(input_file=input_file,
             output_file=output_file,
             pre_post_checks=True,
             vdatum_check=True
            )
