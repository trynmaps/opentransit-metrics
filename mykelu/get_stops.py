import json
import requests

from datetime import datetime, timedelta, timezone, time, date
from itertools import product
from functools import reduce
from eclipses import query_graphql, produce_stops, produce_buses, find_eclipses, find_nadirs

import pandas as pd
import numpy as np

def get_stops(dates, routes, directions = [], new_stops = [], timespan = ("00:00", "23:59")):
    """
    get_stops
    
    Description:
        Returns every instance of a bus stopping at a given set of stops, on a given set of routes, during a given time period.

    Parameters:
        dates: an array of dates, formatted as strings in the form YYYY-MM-DD
        routes: an array of routes, each represented as a string
        directions: an array of strings representing the directions to filter
        stops: an array of strings representing the stops to filter
        times: a tuple with the start and end times (in UTC -8:00) as strings in the form HH:MM 

    Returns:
        stops: a DataFrame, filtered by the given directions and stops, with the following columns:
            VID: the vehicle ID
            Time: a datetime object representing the date/time of the stop
            Route: the route on which the stop occurred
            Stop: the stop at which the stop occurred
            Dir: the direction in which the stop occurred
    """
    bus_stops = pd.DataFrame(columns = ["VID", "DATE", "TIME", "SID", "DID", "ROUTE"])
    
    for route in routes:
        stop_ids = [stop['id']
            for stop
            in requests.get(f"http://restbus.info/api/agencies/sf-muni/routes/{route}").json()['stops']]

        for stop_id in stop_ids:
            # check if stops to filter were provided, or if the stop_id is in the list of filtered stops
            if (stop_id in new_stops) ^ (len(new_stops) == 0):
                for date in dates:
                    print(f"{datetime.now().strftime('%a %b %d %I:%M:%S %p')}: starting processing on stop {stop_id} on route {route} on {date}.")
                    start_time = int(datetime.strptime(f"{date} {timespan[0]} -0800", "%Y-%m-%d %H:%M %z").timestamp())*1000
                    end_time   = int(datetime.strptime(f"{date} {timespan[1]} -0800", "%Y-%m-%d %H:%M %z").timestamp())*1000

                    data = query_graphql(start_time, end_time, route)
                    print(f"{datetime.now().strftime('%a %b %d %I:%M:%S %p')}: performed query.")
                          
                    if data is None:  # API might refuse to cooperate
                        print("API probably timed out")
                        continue
                    elif len(data) == 0:  # some days somehow have no data
                        print(f"no data for {month}/{day}")
                        continue
                    else:
                        stops = produce_stops(data, route)
                        print(f"{datetime.now().strftime('%a %b %d %I:%M:%S %p')}: produced stops.")
                              
                        buses = produce_buses(data)
                        print(f"{datetime.now().strftime('%a %b %d %I:%M:%S %p')}: produced buses.")

                        stop = stops[stops['SID'] == stop_id].squeeze()
                        buses = buses[buses['DID'] == stop['DID']]

                        eclipses = find_eclipses(buses, stop)
                        print(f"{datetime.now().strftime('%a %b %d %I:%M:%S %p')}: found eclipses.")
                              
                        nadirs = find_nadirs(eclipses)
                        print(f"{datetime.now().strftime('%a %b %d %I:%M:%S %p')}: found nadirs.")
                            
                        nadirs["TIME"] = nadirs["TIME"].apply(lambda x: datetime.fromtimestamp(x//1000, timezone(timedelta(hours = -8))))
                        nadirs['DATE'] = nadirs['TIME'].apply(lambda x: x.date())
                        nadirs['TIME'] = nadirs['TIME'].apply(lambda x: x.time())
                        nadirs["SID"] = stop_id
                        nadirs["DID"] = stop["DID"]
                        nadirs["ROUTE"] = route
                        bus_stops = bus_stops.append(nadirs, sort = True)
                        print(f"{datetime.now().strftime('%a %b %d %I:%M:%S %p')}: finished processing.")

    # filter for directions
    if len(directions) > 0:
        bus_stops = bus_stops.loc[bus_stops['DID'].apply(lambda x: x in directions)]

    # prepare timestamp data
    bus_stops['timestamp'] = bus_stops[['DATE', 'TIME']].apply(lambda x: datetime.strptime(f"{x['DATE'].isoformat()} {x['TIME'].isoformat()} -0800", 
                                                                                       "%Y-%m-%d %H:%M:%S %z"), axis = 'columns')

    
    return bus_stops

# a faster implementation of get_wait_times
def get_wait_times(df, dates, timespan, group):
    """
    get_wait_times
    
    Description:
        Takes a DataFrame containing stops for a given route/timespan and returns the corresponding waiting times in that timespan.
        
    Parameters:
        df: a DataFrame containing stop times for a given route/timespan/date interval.
        dates: the range of dates over which to retrieve wait times.
        timespan: the timespan to compute wait times for.
        group: the columns to group over. Needed for sorting.
    
    Returns:
        wait_times: a DataFrame containing the waiting times over the given parameters.
    """
    print(f"{datetime.now().strftime('%a %b %d %I:%M:%S %p')}: starting!")
    
    # sort the DataFrame by time first
    df = df.sort_values(['timestamp']).reset_index()
    wait_times = pd.DataFrame(columns = [])      
    filters = product(*[df[s].unique() for s in group])
    filters = [{group[i]:filter[i] for i in range(len(group))} for filter in filters]
          
    # include day range, take from dates       
    for filter in filters:
        filtered_waits = pd.DataFrame(columns = [])
        filtered_stops = df.loc[reduce((lambda x, y: x & y), [df.apply(lambda x: x[key] == filter[key], axis = 1) for key in filter.keys()]), :]
        start_time = datetime.strptime(f"{filter['DATE'].isoformat()} {timespan[0]} -0800", "%Y-%m-%d %H:%M %z")
        end_time   = datetime.strptime(f"{filter['DATE'].isoformat()} {timespan[1]} -0800", "%Y-%m-%d %H:%M %z")
        minute_range = [start_time + timedelta(minutes = i) for i in range((end_time - start_time).seconds//60)]
        current_index = 0

        for minute in minute_range:
            while current_index < len(filtered_stops):
                if filtered_stops.iloc[current_index]['timestamp'] >= minute:
                    break
                else:
                    current_index += 1
                                       
            # catches the case where current_stops = len(filtered_stops)
            try:
                filtered_waits = filtered_waits.append(filtered_stops.iloc[current_index])
            except:
                filtered_waits = filtered_waits.append(filtered_stops.iloc[-1])

        filtered_waits.index = range(len(filtered_waits))
        filtered_waits['MINUTE'] = pd.Series(minute_range)
        wait_times = wait_times.append(filtered_waits)

    wait_times['WAIT'] = wait_times.apply(lambda x: (x['timestamp'] - x['MINUTE']).total_seconds(), axis = 'columns')
    wait_times.index = range(len(wait_times))
    wait_times['MINUTE'] = wait_times['MINUTE'].apply(lambda x: x.time())
    print(f"{datetime.now().strftime('%a %b %d %I:%M:%S %p')}: finishing!")
    return wait_times[['MINUTE', 'WAIT'] + group]

def quantiles(series):
    return [np.percentile(series, i) for i in [5, 25, 50, 75, 95]]

def get_summary_statistics(df, group):
    waits = df.pivot_table(values = ['WAIT'], index = group, aggfunc = {'WAIT': [np.mean, np.std, quantiles]}).reset_index()
    waits.columns = ['_'.join(col) if col[0] == 'WAIT' else ''.join(col) for col in waits.columns.values]
    waits[[f"{i}th percentile" for i in [5, 25, 50, 75, 95]]] = waits['WAIT_quantiles'].apply(lambda x: pd.Series(x))
    waits = waits.drop('WAIT_quantiles', axis = 1)
    return waits