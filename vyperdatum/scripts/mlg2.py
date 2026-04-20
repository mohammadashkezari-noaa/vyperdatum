from vyperdatum.transformer import Transformer


if __name__ == "__main__":

    input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\point\MLG\Original\AR_01_BAR_20240117_PR\AR_01_BAR_20240117_PR.XYZ"
    crs_from = "ESRI:103295+NOAA:86"  # must be NOAA:66, just testing since depth datum fails currently
    crs_to = "EPSG:6344+NOAA:101"

    tf = Transformer(crs_from=crs_from,
                     crs_to=crs_to
                     )
    output_file = input_file.replace("Original", "Manual")
    tf.transform(input_file=input_file,
                 output_file=output_file,
                 pre_post_checks=True,
                 vdatum_check=False
                 )
