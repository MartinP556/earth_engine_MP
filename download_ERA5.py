import cdsapi
import numpy as np
import pandas as pd
import os
import argparse
import argument_names

parser = argument_names.define_parser()
args = parser.parse_args()

startpoint = np.int64(args.start)
endpoint = np.int64(args.end)

c_CIMMYT = pd.read_csv("Saved_files/CIMMYT_coords_2000_2007.csv")
c_CIMMYT = c_CIMMYT.drop_duplicates(subset = ['lat', 'lon', 'sitecode'])
c_CIMMYT = c_CIMMYT[['lat', 'lon', 'sitecode']].values
c_TA = pd.read_csv("Saved_files/TAMASA_Tanzania_coords.csv").drop_duplicates(subset=['station'])#'lat', 'lon', 
c_TA = c_TA[['lat', 'lon', 'station']].values
#, 'GPS Coordinate Latitude', 'GPS Coordinate Longitude' for including the precise GPS (little change so far)
c_ET = pd.read_csv("Saved_files/TAMASA_Ethiopia_coords.csv").drop_duplicates(subset=['station'])
c_ET = c_ET[['GPS Coordinate Latitude', 'GPS Coordinate Longitude', 'station']].values #

coords = c_CIMMYT[startpoint:endpoint]
#for coord_index, coord in enumerate(coords):
#    print([coord[0] + 0.5, coord[1] - 0.5, coord[0] - 0.5, coord[1] + 0.5])
#client = cdsapi.Client()
#client.retrieve(dataset, request).download()
for year in range(2019, 2025):#range(1999, 2010):#[]:
    dataset = "reanalysis-era5-land"
    request = {
        "variable": [#"total_precipitation", 
            "2m_temperature", "2m_dewpoint_temperature" #"surface_solar_radiation_downwards", "total_precipitation"   #"vapour_pressure"
        ],
#        "statistic": ["24_hour_mean"],
        "year": year,
        "month": [
            "01", "02", "03",
            "04", "05", "06",
            "07", "08", "09",
            "10", "11", "12"
        ],
        "day": [
            "01", "02", "03",
            "04", "05", "06",
            "07", "08", "09",
            "10", "11", "12",
            "13", "14", "15",
            "16", "17", "18",
            "19", "20", "21",
            "22", "23", "24",
            "25", "26", "27",
            "28", "29", "30",
            "31"
        ],
        "time": [
            #"00:00", "01:00", "02:00",
            #"03:00", "04:00", "05:00",
            #"06:00", "07:00", "08:00",
            #"09:00", "10:00", "11:00",
            #"12:00", "13:00", "14:00",
            #"15:00", "16:00", "17:00",
            #"18:00", "19:00", "20:00",
            #"21:00", "22:00", "23:00"
            "00:00", "03:00", "06:00",
            "09:00", "12:00", "15:00",
            "18:00", "21:00"
        ],
        "data_format": "netcdf",
        "download_format": "unarchived",
#        "version": "2_0",
        "area": [12.5, 11.5, -30.5, 40.5]#[56, 5, 47, 16]#[12.5, 11.5, -30.5, 40.5]#[coord[0] + 0.5, coord[1] - 0.5, coord[0] - 0.5, coord[1] + 0.5]#
    }
    client = cdsapi.Client()
    #if isinstance(coord[2], str):
    #    sitename = coord[2]
    #else:
    #    sitename = int(np.round(coord[2]))
    #os.chdir(f'/home/users/wlwc1989/earth_engine_MP/ERA5 land/Africa/CIMMYT/location_{sitename}/year_{year}/')
    os.chdir(f'/home/users/wlwc1989/earth_engine_MP/ERA5 land/Africa/All_Vars/d2m_t2m/{year}/')#Africa/CIMMYT/All_Africa/
    client.retrieve(dataset, request).download()#ERA5_{sitename}_{year}.nc