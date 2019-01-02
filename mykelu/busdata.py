import json

from typing import List


class BusData:
    def __init__(self):
        """
        `data` format:

        {
            route_id: {  # route_id is a str
                stop_id: {  # stop_id is a str
                    direction_id: str,
                    order: int,
                    lat: float,
                    lon: float,
                    eclipses: [
                        {
                            bus_id: int,
                            timestamp: int,
                        },
                        {
                            bus_id: int,
                            timestamp: int,
                        },
                        ...
                    ]
                },
                ...
            },
            ...
        }

        """
        self.data = {}

    def routes(self) -> List[str]:
        """Returns contained routes"""
        return list(self.data.keys())

    def stops(self, route_id: str) -> List[str]:
        """Returns contained stops for a given route"""
        return list(self.data.get(route_id, {}).keys())

    def append(self, other_data: dict):
        """Merges `other_data` into `self.data`, creating new entries as needed"""
        for route_id, other_route in other_data.items():
            route = self.data.get(route_id)
            if route:
                for stop_id, other_stop in other_route.items():
                    stop = route.get(stop_id)
                    if stop:
                        stop['eclipses'].extend(other_stop['eclipses'])
                    else:
                        route[stop_id] = other_stop
            else:
                self.data[route_id] = other_route

    @classmethod
    def read_file(cls, filename: str) -> 'BusData':
        """Creates new `BusData` with data from file `filename`"""
        bus_data = cls()
        with open(filename, 'r') as f:
            bus_data.append(json.load(f))
        return bus_data


    def write_file(self, filename: str):
        """Writes `self.data` into file `filename`"""
        with open(filename, 'w') as f:
            json.dump(self.data, f)
