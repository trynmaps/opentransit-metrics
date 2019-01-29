import json
import requests

from datetime import datetime, timedelta, timezone

import pandas as pd
import numpy as np
from geopy.distance import distance

from typing import List, Union
from eclipses import query_graphql, produce_stops, produce_buses, find_eclipses, find_nadirs

# get_stops
# ------------------------------------------------------------------------------------------
# parameters:
# dates: an array of dates, formatted as strings in the form YYYY-MM-DD
# routes: an array of routes, each represented as a string
# directions: an array of strings representing the directions to filter
# stops: an array of strings representing the stops to filter
# times: a tuple with the start and end times (in UTC -8:00) as strings in the form HH:MM 
# 
# returns:
# stops: a DataFrame, filtered by the given directions and stops, with the following columns:
# VID: the vehicle ID
# Time: a datetime object representing the date/time of the stop
# Route: the route on which the stop occurred
# Stop: the stop at which the stop occurred
# Dir: the direction in which the stop occurred
# -------------------------------------------------------------------------------------------
def get_stops(dates, routes, directions = [], new_stops = [], times = ("00:00", "23:59")):
    bus_stops = pd.DataFrame(columns = ["VID", "TIME", "SID", "DID", "ROUTE"])
    
    for route in routes:
        stop_ids = [stop['id']
            for stop
            in requests.get(f"http://restbus.info/api/agencies/sf-muni/routes/{route}").json()['stops']][2:4]

        for stop_id in stop_ids:
            # TODO: move stop check here
            for date in dates:
                start_time = int(datetime.strptime(f"{date} {timespan[0]} -0800", "%Y-%m-%d %H:%M %z").timestamp())*1000
                end_time   = int(datetime.strptime(f"{date} {timespan[1]} -0800", "%Y-%m-%d %H:%M %z").timestamp())*1000

                data = query_graphql(start_time, end_time, route)

                if data is None:  # API might refuse to cooperate
                    print("API probably timed out")
                    continue
                elif len(data) == 0:  # some days somehow have no data
                    print(f"no data for {month}/{day}")
                    continue
                else:
                    stops = produce_stops(data, route)
                    buses = produce_buses(data)

                    stop = stops[stops['SID'] == stop_id].squeeze()
                    buses = buses[buses['DID'] == stop['DID']]

                    eclipses = find_eclipses(buses, stop)
                    nadirs = find_nadirs(eclipses)
                    nadirs["TIME"] = nadirs["TIME"].apply(lambda x: datetime.fromtimestamp(x//1000, timezone(timedelta(hours = -8))).strftime('%a %b %d %I:%M%p'))
                    nadirs["SID"] = stop_id
                    nadirs["DID"] = stop["DID"]
                    nadirs["ROUTE"] = route
                    old_length = len(bus_stops)
                    bus_stops = bus_stops.append(nadirs, sort = True)
                    print(f"{datetime.now().strftime('%a %b %d %I:%M:%S %p')}: Stop {stop['SID']} on route {route} on {date} is done! {len(nadirs)} rows processed! {len(bus_stops) - old_length} rows added to stops!")
    
    # filter for diretions and stops
    if len(directions) > 0:
        bus_stops = bus_stops.loc[bus_stops['DID'].apply(lambda x: x in directions)]

    if len(new_stops) > 0:
        bus_stops = bus_stops.loc[bus_stops['SID'].apply(lambda x: x in new_stops)]
    
    return bus_stops

if __name__ == "__main__":
    route = ["12", "14"]

    timespan = ("08:00",
                "11:00")

    dates = [
        "2018-11-12",
        "2018-11-13",
        "2018-11-14",
        "2018-11-15",
        "2018-11-16",
    ]

    new_stops = get_stops(dates, route, times = timespan)
    print(new_stops)