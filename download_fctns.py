import ee
import pandas as pd

class timeseries_downloader:
    def __init__(self, coords):
        self.coords = coords
        
    def initiate_image_collection(self, instrument = "COPERNICUS/S2_SR_HARMONIZED", bands = ['B4', 'B8'], 
                                  start_date = '2000-01-01', end_date = '2022-12-31', 
                                  QC_function = mask_s2_clouds_collection):
        self.bands = bands
        self.dataset = ee.ImageCollection(instrument).filterDate(start_date, end_date)
        self.dataset = QC_function(self.dataset)
        self.dataset = self.dataset.select(*bands)
        
    def read_at_coords(self, box_width = 0.002):
        for coord_index, coord in enumerate(self.coords):
            location = box_around_point(coord, box_width)
            filtered_dataset = reduce_region_collection(dataset, location, reducer_code = 'median', pixel_scale = pixel_scale)
            df = collection_properties_to_frame(filtered_dataset, coord, self.bands, reducer_code = 'median')
            if coord_index == 0:
                self.df_full = df
            else:
                self.df_full = pd.concat([df_full, df])

def box_around_point(coord, box_width):
    '''
    coord: coordinate in (lat, lon) (?)
    '''
    return ee.Geometry.BBox(coord[1] - box_width, coord[0] - box_width, coord[1] + box_width, coord[0] + box_width)

def get_mean(image, location, pixel_scale= 500):
    return image.set('mean', image.reduceRegion(ee.Reducer.mean(), location , pixel_scale))

def get_median(image, location, pixel_scale= 500):
    return image.set('median', image.reduceRegion(ee.Reducer.median(), location , pixel_scale))

def reduce_region_collection(image_collection, location, reducer_code = 'median', pixel_scale = 500):
    if reducer_code == 'mean':
        return image_collection.map(lambda img: get_mean(img, location, pixel_scale = pixel_scale))
    elif reducer_code == 'median':
        return image_collection.map(lambda img: get_median(img, location, pixel_scale = pixel_scale))
    else:
        print('invalid reducer code')

def collection_properties_to_frame(image_collection, coord, bands, reducer_code = 'median'):
    timelist = image_collection.aggregate_array('system:time_start').getInfo()
    bandlist = image_collection.aggregate_array('median').getInfo()
    data = {'Time': timelist,
            'lat': [coord[0] for count in range(len(timelist))],
            'lon': [coord[1] for count in range(len(timelist))],
            'Stations_Id': [np.int64(coord[2]) for count in range(len(timelist))]
           }
    for band in bands:
        data[f'{reducer_code} {band}'] = [band_data[band] for band_data in bandlist]
    df = pd.DataFrame(data)
    df['formatted_time'] = pd.to_datetime(df['Time'], unit='ms').dt.strftime('%Y-%m-%d-%H-%M-%S')
    return df

def satellite_data_at_coords(coords, start_date = '2000-01-01', end_date = '2022-12-31', instrument = "COPERNICUS/S2_SR_HARMONIZED", bands = ['B4', 'B8'], box_width = 0.002, pixel_scale = 500, QC_function = mask_s2_clouds_collection):
    dataset = ee.ImageCollection(instrument).filterDate(start_date, end_date)
    dataset = QC_function(dataset)
    for coord_index, coord in enumerate(coords):
        print(coord_index)
        location = box_around_point(coord, box_width)
        filtered_dataset = dataset.filterBounds(location)
        filtered_dataset = filtered_dataset.select(*bands)
        .map(lambda img: img.set('median', img.reduceRegion(ee.Reducer.median(), location , pixel_scale)))
        timelist = filtered_dataset.aggregate_array('system:time_start').getInfo()
        bandlist = filtered_dataset.aggregate_array('median').getInfo()
        dataset = {'Time': timelist,
                   'lat': [coord[0] for count in range(len(timelist))],
                   'lon': [coord[1] for count in range(len(timelist))],
                   'Stations_Id': [np.int64(coord[2]) for count in range(len(timelist))]
                   }
        for band in bands:
            dataset[f'Median {band}'] = [band_data[band] for band_data in bandlist]
        df = pd.DataFrame(dataset)
        df['formatted_time'] = pd.to_datetime(df['Time'], unit='ms').dt.strftime('%Y-%m-%d-%H-%M-%S')
        if coord_index == 0:
            df_full = df
        else:
            df_full = pd.concat([df_full, df])
    return df_full