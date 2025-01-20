import ee
from google.oauth2 import service_account
import numpy as np
import pandas as pd
import argparse
import argument_names
from masks import mask_MODIS_clouds, MODIS_Mask_QC, mask_s2_clouds, mask_s2_clouds_collection
import download_fctns
import cProfile, pstats, io
from pstats import SortKey

parser = argument_names.define_parser()
args = parser.parse_args()

startpoint = np.int64(args.start)
endpoint = np.int64(args.end)
savename = args.savename
print(startpoint, endpoint, savename)
# Path to the private key file
key_path = 'Access/ee-martinparker637-e68fde65abb4.json'

# Load the service account credentials
credentials = service_account.Credentials.from_service_account_file(
    key_path,
    scopes=['https://www.googleapis.com/auth/earthengine'])

# Initialize Earth Engine with the service account credentials
ee.Initialize(credentials)

root_directory = ''#'home/users/wlwc1989/phenology_dwd/'
#root_directory = 'C:\\Users\\wlwc1989\\Documents\\Phenology_Test_Notebooks\\phenology_dwd\\'



#df = satellite_data_at_coords(coords[startpoint:endpoint], start_date='2000-10-01')

pr = cProfile.Profile()
pr.enable()
# ... do something ...
#df = satellite_data_at_coords(coords[startpoint:endpoint], start_date='2000-01-01', instrument = "MODIS/061/MOD09GA", QC_function = lambda IC: IC.map(MODIS_Mask_QC).map(mask_MODIS_clouds), bands = [f'sur_refl_b0{n}' for n in range(1, 5)])

coords = np.loadtxt(root_directory + "Saved_files/station_coords.csv", delimiter=',')
MODIS_downloader = download_fctns.timeseries_downloader(coords[startpoint:endpoint])
MODIS_downloader.initiate_image_collection(
    instrument = "MODIS/061/MOD09GA", bands = [f'sur_refl_b0{n}' for n in range(1, 5)],
    start_date = '2020-01-01', 
    QC_function = lambda IC: IC.map(MODIS_Mask_QC).map(mask_MODIS_clouds))
MODIS_downloader.read_at_coords(box_width = 0.002)
MODIS_downloader.df_full.dropna().to_csv(root_directory + f"Saved_files/{savename}.csv")

#df.dropna().to_csv(root_directory + f"Saved_files/{savename}.csv")

pr.disable()
s = io.StringIO()
sortby = SortKey.CUMULATIVE
ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
ps.print_stats()
print(s.getvalue())