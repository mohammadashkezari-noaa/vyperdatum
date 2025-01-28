import os
import glob
import pathlib
import pandas as pd
from vyperdatum.transformer import Transformer



# import pyproj as pp
# import sys
# xt, yt, zt = pp.Transformer.from_crs(crs_from="ESRI:102445",
#                                      crs_to="EPSG:6318",
#                                      always_xy=True,
#                                      only_best=True
#                                      ).transform([1330693.71], [2794306.28], [0])

# print(xt, yt, zt)
# sys.exit()




import sys
import pyproj
xt, yt, zt = pyproj.Transformer.from_crs(crs_from="EPSG:9990+NOAA:101",
                                         crs_to="EPSG:9990+EPSG:5703",
                                         always_xy=True,
                                         only_best=True
                                         ).transform([-133.143], [55.475], [0])
print(xt, yt, zt)
sys.exit()



if __name__ == "__main__":
    files = glob.glob(r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\point\USACE\PBA\Original\**\*.XYZ", recursive=True)


    crs_from = "ESRI:102445+NOAA:5537"
    crs_to = "EPSG:9000+EPSG:5703"    # ITRF2008 + MSL (XGEOID17B_ALASKA) depth


    steps = [
            # {"crs_from": "ESRI:102445", "crs_to": "EPSG:6319"},
            # {"crs_from": "EPSG:6319", "crs_to": "EPSG:7911"},
            # {"crs_from": "EPSG:8999+NOAA:5536", "crs_to": "EPSG:8999+EPSG:5703"}

            {"crs_from": "ESRI:102445", "crs_to": "EPSG:6319"},
            {"crs_from": "EPSG:6319", "crs_to": "EPSG:7912"},
            {"crs_from": "EPSG:7912", "crs_to": "EPSG:9989"},
            {"crs_from": "EPSG:9990+NOAA:101", "crs_to": "EPSG:9990+EPSG:5703"}

            ]

    for i, input_file in enumerate(files[:1]):
        print(f"{i+1}/{len(files)}: {input_file}")
        df = pd.read_csv(input_file, sep=",", names=["x", "y", "z"], skiprows=19)
        x, y, z = df.x.values, df.y.values, df.z.values
        tf = Transformer(crs_from=crs_from,
                         crs_to=crs_to,
                         steps=steps
                         )
        xt, yt, zt = tf.transform_points(x, y, z,
                                         always_xy=True,
                                         allow_ballpark=False,
                                         only_best=True,
                                         vdatum_check=False)
        output_file = input_file.replace("Original", "Manual")
        pathlib.Path(os.path.split(output_file)[0]).mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"x": xt, "y": yt, "z": zt}).to_csv(output_file+".csv", index=False)
        
        df.to_csv(output_file+"_input.csv", index=False)

        # print(f'\n{"*"*50} {i+1}/{len(files)} Completed {"*"*50}\n')
