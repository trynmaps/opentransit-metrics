import json
import requests

from datetime import datetime, timedelta, timezone

import pandas as pd
import numpy as np
from geopy.distance import distance

from typing import List, Union

def query_graphql(start_time: int, end_time: int, route: str) -> list:
    query = f"""{{
        trynState(agency: "muni",
                  startTime: "{start_time}",
                  endTime: "{end_time}",
                  routes: ["{route}"]) {{
            agency
            startTime
            routes {{
                stops {{
                    sid
                    lat
                    lon
                }}
                routeStates {{
                    vtime
                    vehicles {{
                        vid
                        lat
                        lon
                        did
                    }}
                }}
            }}
        }}
    }}
    """
    query_url = f"https://06o8rkohub.execute-api.us-west-2.amazonaws.com/dev/graphql?query={query}"

    request = requests.get(query_url).json()
    try:
        return request['data']['trynState']['routes']
    except KeyError:
        return None

def produce_stops(data: list, route: str) -> pd.DataFrame:
    stops = pd.io.json.json_normalize(data,
                                      record_path=['stops']) \
            .rename(columns={'lat': 'LAT',
                             'lon': 'LON',
                             'sid': 'SID'}) \
            .reindex(['SID', 'LAT', 'LON'], axis='columns')
    
    # obtain stop directions
    stops['DID'] = stops['SID'].map({stop: direction['id']
                                     for direction in requests
                                                      .get(f"http://restbus.info/api/agencies/sf-muni/routes/{route}")
                                                      .json()['directions']
                                     for stop in direction['stops']})
    
    # remove stops that don't have an associated direction
    stops = stops.dropna(axis='index', subset=['DID'])
    
    # obtain stop ordinals
    stops['ORD'] = stops['SID'].map({stop_meta['id']: ordinal
                                     for ordinal, stop_meta
                                     in enumerate(requests
                                                  .get("http://restbus.info/api/agencies/sf-muni/"
                                                       f"routes/{route}")
                                                  .json()['stops'])})
    
    return stops

def produce_buses(data: list) -> pd.DataFrame:
     return pd.io.json.json_normalize(data,
                                      record_path=['routeStates', 'vehicles'],
                                      meta=[['routeStates', 'vtime']]) \
            .rename(columns={'lat': 'LAT',
                             'lon': 'LON',
                             'vid': 'VID',
                             'did': 'DID',
                             'routeStates.vtime': 'TIME'}) \
            .reindex(['TIME', 'VID', 'LAT', 'LON', 'DID'], axis='columns')

def find_eclipses(buses, stop):
    """
    Find movement of buses relative to the stop, in distance as a function of time.
    """
    def split_eclipses(eclipses, threshold=30*60*1000) -> List[pd.DataFrame]:
        """
        Split buses' movements when they return to a stop after completing the route.
        """
        disjoint_eclipses = []
        for bus_id in eclipses['VID'].unique():
            # obtain distance data for this bus
            bus = eclipses[eclipses['VID'] == bus_id].sort_values('TIME')

            # split data into groups when there is at least a `threshold`-ms gap between data points
            group_ids = (bus['TIME'] > (bus['TIME'].shift() + threshold)).cumsum()

            # store groups
            for _, group in bus.groupby(group_ids):
                disjoint_eclipses.append(group)
        return disjoint_eclipses

    eclipses = buses.copy()
    
    eclipses['DIST'] = eclipses.apply(lambda bus: distance(stop[['LAT', 'LON']],
                                                           bus[['LAT', 'LON']]).meters,
                                      axis='columns')
    eclipses['TIME'] = eclipses['TIME'].astype(np.int64)
    eclipses = eclipses[['TIME', 'VID', 'DIST']]
    
    # only keep positions within 750 meters
    eclipses = eclipses[eclipses['DIST'] < 750]
    
    eclipses = split_eclipses(eclipses)
    
    return eclipses

def find_nadirs(eclipses):
    """
    Find points where buses are considered to have encountered the stop.
    
    Nadir is an astronomical term that describes the lowest point reached by an orbiting body.
    """
    def calc_nadir(eclipse: pd.DataFrame) -> Union[pd.Series, None]:
        nadir = eclipse.iloc[eclipse['DIST'].values.argmin()]
        if nadir['DIST'] < 100:  # if min dist < 100, then reasonable candidate for nadir
            return nadir
        else:  # otherwise, hardcore datasci is needed
            rev_eclipse = eclipse.iloc[::-1]
            rev_nadir = rev_eclipse.iloc[rev_eclipse['DIST'].values.argmin()]
            if nadir['TIME'] == rev_nadir['TIME']:  # if eclipse has a global min
                return nadir  # then it's the best candidate for nadir
            else:  # if eclipse's min occurs at two times
                mid_nadir = nadir.copy()
                mid_nadir['DIST'] = (nadir['DIST'] + rev_nadir['DIST'])/2
                return mid_nadir  # take the midpoint of earliest and latest mins
    
    nadirs = []
    for eclipse in eclipses:
        nadirs.append(calc_nadir(eclipse)[['VID', 'TIME']])
        
    return pd.DataFrame(nadirs)