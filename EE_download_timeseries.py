import ee
from google.oauth2 import service_account
import numpy as np
import pandas as pd
import argparse
import argument_names
from masks import mask_MODIS_clouds, MODIS_Mask_QC, mask_s2_clouds, mask_s2_clouds_collection, worldcereal_mask, csPlus_mask_collection, MODIS_mask_clouds_250m
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

coords = np.loadtxt(root_directory + "Saved_files/station_coords_MODIS.csv", delimiter=',')
#coords = []
#for lat in np.arange(-1, 1, 0.05):
#    for lon in np.arange(35.05, 37.05, 0.05):
#        coords.append([lat , lon, 0])
for year in [2017, 2018, 2019, 2020, 2021, 2022]:
    MODIS_downloader = download_fctns.timeseries_downloader(coords[startpoint:endpoint])
    MODIS_downloader.initiate_image_collection(
        instrument = "MODIS/061/MOD09GQ", bands = ['sur_refl_b01', 'sur_refl_b02', 'NDVI'],#[f'sur_refl_b0{n}' for n in range(1, 5)],
        start_date = f'{year}-01-01', end_date = f'{year}-12-31',
        QC_function = MODIS_mask_clouds_250m #lambda IC: IC.map(mask_MODIS_clouds)
    )
    MODIS_downloader.read_at_coords(buffer_size = 5000, loc_type = 'point', mask_to_use = 'Thuenen',
                                   count_threshold = 600, mask_scale = 250,)
    MODIS_downloader.df_full.dropna().to_csv(root_directory + f"Saved_files/{savename}_{year}.csv")

#Sentinel_downloader = download_fctns.timeseries_downloader(coords[startpoint:endpoint])
#Sentinel_downloader.initiate_image_collection(
#        instrument = "COPERNICUS/S2_SR_HARMONIZED", bands = ['EVI','NDVI', 'SAVI', 'NDWI', 'CIG'], #bands = [f'B{n}' for n in range(4, 9)] + ['NDVI'],
#    start_date = '2017-01-01', end_date = '2024-12-31', 
#    QC_function = csPlus_mask_collection, 
#    pixel_scale = 250, get_NDVI = True,
#    indices = True
#)
#    lambda IC: csPlus_mask_collection(IC.map(worldcereal_mask).map(mask_s2_clouds)) #
#    QC_function = lambda IC: IC.map(MODIS_Mask_QC).map(mask_MODIS_clouds))
#Sentinel_downloader.read_at_coords(buffer_size = 1500, loc_type = 'random_points')
#Sentinel_downloader.df_full.dropna().to_csv(root_directory + f"Saved_files/{savename}.csv")

#df.dropna().to_csv(root_directory + f"Saved_files/{savename}.csv")

pr.disable()
s = io.StringIO()
sortby = SortKey.CUMULATIVE
ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
ps.print_stats()
print(s.getvalue())
