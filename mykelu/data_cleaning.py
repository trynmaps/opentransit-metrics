import requests

import pandas as pd


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
    except KeyError:  # connection timeout or no data
        return None


def produce_stops_df(data: list, route_meta: dict) -> pd.DataFrame:
    stops = pd.io.json.json_normalize(data,
                                      record_path=['stops']) \
            .rename(columns={'lat': 'LAT',
                             'lon': 'LON',
                             'sid': 'SID'}) \
            .reindex(['SID', 'LAT', 'LON'], axis='columns')

    # obtain stop directions
    stops['DID'] = stops['SID'].map({stop: direction['id']
                                     for direction in route_meta['directions']
                                     for stop in direction['stops']})

    # remove stops that don't have an associated direction
    stops = stops.dropna(axis='index', subset=['DID'])

    # obtain stop ordinals
    stops['ORD'] = stops['SID'].map({stop_meta['id']: ordinal
                                     for ordinal, stop_meta
                                     in enumerate(route_meta['stops'])})

    return stops


def produce_buses_df(data: list) -> pd.DataFrame:
     return pd.io.json.json_normalize(data,
                                      record_path=['routeStates', 'vehicles'],
                                      meta=[['routeStates', 'vtime']]) \
            .rename(columns={'lat': 'LAT',
                             'lon': 'LON',
                             'vid': 'VID',
                             'did': 'DID',
                             'routeStates.vtime': 'TIME'}) \
            .reindex(['TIME', 'VID', 'LAT', 'LON', 'DID'], axis='columns')
