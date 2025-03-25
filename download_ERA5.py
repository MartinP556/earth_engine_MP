import cdsapi

for year in [2009, 2010, 2002, 2003, 2001]:
    dataset = "reanalysis-era5-land"
    request = {
        "variable": [
            "2m_dewpoint_temperature",
            "2m_temperature",
            "surface_solar_radiation_downwards",
            "total_precipitation"
        ],
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
            "00:00", "03:00", "06:00",
            "09:00", "12:00", "15:00",
            "18:00", "21:00"
        ],
        "data_format": "netcdf",
        "download_format": "unarchived",
        "area": [56, 5, 47, 16]
    }
    
    client = cdsapi.Client()
    client.retrieve(dataset, request).download()