import json
import requests

from datetime import datetime



def query_graphql(start_time: int, end_time: int, route: str, sid: int, did: str) -> list:
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

if __name__ == "__main__":
    date = "2018-11-12"
    timespan = ("08:00", "11:00")
    start_time = int(datetime.strptime(f"{date} {timespan[0]} -0800", "%Y-%m-%d %H:%M %z").timestamp())*1000
    end_time   = int(datetime.strptime(f"{date} {timespan[1]} -0800", "%Y-%m-%d %H:%M %z").timestamp())*1000
    route = "14"
    sid = 5579
    did = "14___O_F00"

    print(query_graphql(start_time, end_time, route, sid, did)[0])