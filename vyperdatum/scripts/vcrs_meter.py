from vyperdatum.db import DB
import pyproj as pp

def meter_none_NOAA_vcrs(auth_code):
    """
    Takes a VCRS auth_code. If it's in meters, returns itself.
    If not, returns the auth_code of the identical VCRS in meters.
    """
    if auth_code is None:
        return None
    crs = pp.CRS.from_user_input(auth_code)
    auth_name = auth_code.split(':')[0]
    
    crs_dict = crs.to_json_dict()
    axis_info = crs_dict['coordinate_system']['axis'][0]    
    current_unit = axis_info.get('unit')
    
    if current_unit == "metre":
        return auth_code

    target_datum = crs_dict.get('datum', {}).get('name')
    target_dir = axis_info.get('direction').lower()
    target_bbox = crs_dict.get('bbox')
    
    codes = pp.get_codes(auth_name, "VERTICAL_CRS", allow_deprecated=True)
    best_match = None    
    for code in codes:
        full_code = f"{auth_name}:{code}"
        if full_code == auth_code:
            continue
            
        candidate_crs = pp.CRS.from_user_input(full_code)
        cand_dict = candidate_crs.to_json_dict()
        cand_axis = cand_dict['coordinate_system']['axis'][0]
        
        if cand_axis.get('unit') != "metre":
            continue
            
        cand_datum = cand_dict.get('datum', {}).get('name')
        cand_dir = cand_axis.get('direction').lower()
        
        if cand_datum == target_datum and cand_dir == target_dir:
            if cand_dict.get('bbox') == target_bbox:
                return full_code            
            best_match = full_code

    if best_match:
        return best_match
    raise ValueError(f"Could not find a meter-based version of {auth_code} in {auth_name}.")

def meter_NOAA_vcrs(auth_code):
    """
    Takes a VCRS auth_code. If it's in meters, returns itself.
    If not, returns the auth_code of the identical VCRS in meters.
    """
    if auth_code is None:
        return None
    vname, vcode = auth_code.split(":")
    vname = vname.upper()
    sql = f"""
        select *, v.name as vname, a.name as aname from vertical_crs v 
        join axis a on a.coordinate_system_code = v.coordinate_system_code
        where v.auth_name='{vname}' and v.code={vcode}
    """
    df = DB().query(sql, dataframe=True)
    if df is None or df.empty:
        raise ValueError(f"CRS {auth_code} not found in database.")
    row = df.iloc[0]
    if row["uom_code"] == 9001: # already meter
        return auth_code
    
    version = None
    nwld_clue = "National_Water_Level_Datum/nwldatum_"
    if nwld_clue in row.vname:
        version = row.vname.split(nwld_clue)[1].split("_")[0]
    sql = f"""
        select * from vertical_crs v 
        join axis a on a.coordinate_system_code = v.coordinate_system_code
        where 
        v.auth_name='{vname}'
        and v.description='{row.description}' 
        and v.datum_auth_name='{row.datum_auth_name}' 
        and v.datum_code={row['datum_code']} 
        and a.name='{row.aname}'
        and a.orientation='{row.orientation}'
        and a.coordinate_system_order={row.coordinate_system_order}
        and a.uom_code=9001
    """
    if version:
        sql += f" and v.name like '%{version}%'"
    df = DB().query(sql, dataframe=True)
    if df is None or df.empty:
        raise ValueError(f"No VCRS in meters found for {auth_code} in database.")
    if len(df) > 1:
        raise ValueError(f"More than one ({len(df)}) VCRS in meters found for {auth_code} in database.")
    return f"{vname}:{df.iloc[0]['code'].values[0]}"
    
def get_meter_vcrs0(auth_code):
    """
    Takes a VCRS auth_code. If it's in meters, returns itself.
    If not, returns the auth_code of the identical VCRS in meters.
    """
    if auth_code is None:
        return None
    vname, vcode = auth_code.split(":")
    if vname.upper() == "NOAA":
        return meter_NOAA_vcrs(auth_code)
    else:
        return meter_none_NOAA_vcrs(auth_code)
    



def get_meter_vcrs(auth_code):
    if auth_code is None:
        return None
        
    crs = pp.CRS.from_user_input(auth_code)
    auth_name = auth_code.split(':')[0].upper()
    
    crs_dict = crs.to_json_dict()
    axis_info = crs_dict['coordinate_system']['axis'][0]
    
    # 1. Quick exit if already in meters
    if axis_info.get('unit') == "metre":
        return auth_code

    # 2. Extract characteristics for matching
    target_datum = crs_dict.get('datum', {}).get('name')
    target_dir = axis_info.get('direction').lower()
    target_bbox = crs_dict.get('bbox')
    orig_name = crs_dict.get('name', '')

    # 3. Handle NOAA-specific versioning (e.g., "nwldatum_4.7.0")
    version_clue = None
    nwld_clue = "National_Water_Level_Datum/nwldatum_"
    if auth_name == "NOAA" and nwld_clue in orig_name:
        # Extract the version string (e.g., "4.7.0")
        try:
            version_clue = orig_name.split(nwld_clue)[1].split("_")[0]
        except IndexError:
            pass

    # 4. Search the authority
    codes = pp.get_codes(auth_name, "VERTICAL_CRS", allow_deprecated=True)
    best_match = None
    
    for code in codes:
        full_code = f"{auth_name}:{code}"
        if full_code == auth_code:
            continue
            
        candidate_crs = pp.CRS.from_user_input(full_code)
        cand_dict = candidate_crs.to_json_dict()
        cand_axis = cand_dict['coordinate_system']['axis'][0]
        
        # Check Unit, Direction, and Datum
        if cand_axis.get('unit') != "metre":
            continue
        if cand_axis.get('direction').lower() != target_dir:
            continue
        if cand_dict.get('datum', {}).get('name') != target_datum:
            continue

        # 5. Apply the "Version" and "BBox" filters
        cand_name = cand_dict.get('name', '')
        
        # If we have a NOAA version clue, the candidate name MUST contain it
        if version_clue and version_clue not in cand_name:
            continue

        # Perfect match: Same Datum, Direction, Unit, and BBox
        if cand_dict.get('bbox') == target_bbox:
            return full_code
            
        # Fallback match: Same Datum, Direction, Unit (and Version if applicable)
        best_match = full_code

    if best_match:
        return best_match
        
    raise ValueError(f"No meter-based VCRS found for {auth_code} in {auth_name}.")


tblVCRS = {
                "navd88": {"height(m)": "EPSG:5703",
                            "depth(m)": "EPSG:6357",
                            "height(ft)": "EPSG:6360",
                            "depth(ft)": "EPSG:6358"},
                "ngvd29": {"height(m)": "EPSG:7968",
                            "height(ft)": "EPSG:5702",
                            "depth(ft)": "EPSG:6359"},
                "ncd": {"height(m)": "NOAA:101",
                        "depth(m)": "NOAA:100",
                        "height(ft)": "NOAA:25101",
                        "depth(ft)": "NOAA:25100"},
                "hrd": {"height(m)": "NOAA:87",
                        "depth(m)": "NOAA:67",
                        "height(ft)": "NOAA:25087",
                        "depth(ft)": "NOAA:25067"},
                "crd": {"height(m)": "NOAA:88",
                        "depth(m)": "NOAA:68",
                        "height(ft)": "NOAA:25088",
                        "depth(ft)": "NOAA:25068"},
                "lwrp": {"height(m)": "NOAA:89",
                            "depth(m)": "NOAA:69",
                            "height(ft)": "NOAA:25089",
                            "depth(ft)": "NOAA:25069"},
                "mlw": {"height(m)": "NOAA:99",
                        "depth(m)": "NOAA:79",
                        "height(ft)": "NOAA:25099",
                        "depth(ft)": "NOAA:25079"},
                "mllw": {"height(m)": "NOAA:98",
                            "depth(m)": "NOAA:78",
                            "height(ft)": "NOAA:25098",
                            "depth(ft)": "NOAA:25078"},
                "igld85": {"height(m)": "NOAA:92",
                            "depth(m)": "NOAA:72",
                            "height(ft)": "NOAA:25092",
                            "depth(ft)": "NOAA:25072"},
                "igld85lwd": {"height(m)": "NOAA:93",
                                "depth(m)": "NOAA:73",
                                "height(ft)": "NOAA:25093",
                                "depth(ft)": "NOAA:25073"},
                "lwd": {"height(m)": "NOAA:94",
                        "depth(m)": "NOAA:74",
                        "height(ft)": "NOAA:25094",
                        "depth(ft)": "NOAA:25074"},
                "mlg": {"height(m)": "NOAA:86",
                        "depth(m)": "NOAA:66",
                        "height(ft)": "NOAA:25086",
                        "depth(ft)": "NOAA:25066"},
}



for key, val in tblVCRS.items():
    for k, v in val.items():
        try:
            print(f"{key} - {k}: {v}  --->  {get_meter_vcrs(v)}")
        except ValueError as e:
            print(f"{key} - {k}: {v}  --->  Error: {e}")
