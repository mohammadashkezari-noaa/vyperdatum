import os
from vyperdatum.transformer import Transformer
from mlg import XYZ

if __name__ == "__main__":

    
    files = [
        r"C:\Users\Mohammad.Ashkezari\Documents\projects\vyperdatum\untrack\data\point\USACE\PBG\Original\LK_04_PAL_20260224_CS\LK_04_PAL_20260224_CS.XYZ",
        r"C:\Users\Mohammad.Ashkezari\Documents\projects\vyperdatum\untrack\data\point\USACE\PBG\Original\CEMVN_DIS_BH_01_DEV_20260415_CS\BH_01_DEV_20260415_CS.XYZ",
    ]
    crs_from = "EPSG:3452+EPSG:5702"
    crs_to = "EPSG:6344+NOAA:89"

    for input_file in files:
        xyz = XYZ(input_file=input_file)
        df = xyz.transform(crs_from=crs_from, crs_to=crs_to)
        output_file = input_file.replace("Original", "Manual").replace(".XYZ", ".parquet")
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        xyz.to_geoparquet(crs=crs_to, output_file=output_file)

        print(df.head())