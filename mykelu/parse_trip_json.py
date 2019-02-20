import pandas as pd
import json
import re

def load_trips_df(filename):
    """
    Usage: load_trips_df(path_to_json)

    Returns a DataFrame where each row is a vehicle location.
    """
    with open(filename, 'r') as f:
        ret = []
        keys = ('vehicle_id', 'route', 'pattern', 'start_time')
        
        for line in f:
            # parse the keys as a tuple
            split_index = line.find("):")
            key_values = line[2 : split_index].replace("'", '"').split(", ")
            key_dict = {k:v for k, v in zip(keys, key_values)}
            stops = json.loads(line[split_index + 3 : -2].replace("'", '"'))
            
            # add each vehicle location to the list
            for stop in stops:
                ret.append({**stop, **key_dict})
            
        df = pd.DataFrame(ret)

        # memory optimization - downcast columns
        for col in ['start_time', 'time', 'vehicle_id']:
            df[col] = pd.to_numeric(df[col].apply(lambda x: re.sub(r'\D', '', x)))

        for col in ['pattern', 'route']:
            df[col] = df[col].astype('category')

        for col in ['heading', 'lat', 'lon', 'start_time', 'time', 'vehicle_id']:
            df[col] = df[col].apply(pd.to_numeric, downcast = 'unsigned')

        return df