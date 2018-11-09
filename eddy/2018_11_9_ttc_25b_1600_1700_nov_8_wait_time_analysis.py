import datetime
import numpy as np

from ttc_25B_greenbelt_nb_16h_17h_nov_8_18 import ttc_list

# Conclusion: Bunching led to 40% longer average wait times for passengers than scheduled
# at the Don Mills/Greenbelt stop of the TTC 25B route. 
# 11 buses/hour pass that stop, for an expected wait-time of 2.53 minutes; however, based
# on PointReliability endpoint data, on November 9 between 1600 and 1700, 11 buses did pass
# but with some degree of bunching and gaps, with the maximum and minimum headways being
# 12 and 0.5 minutes respectively.

# Note: The PointReliability has not been tested, does not account for fast-moving buses skipping
# stops, and may return inaccurate results. 
# In thie analysis, its results seemed very reasonable given Eddy's familiarity with the route.
# It might be worth comparing to the web-app once it adds support for the TTC.

# TODO - clarify usage in terms of arrival_times
def simulate_wait_times(arrival_times,
                        rseed=8675309,
                        n_passengers=1000000):
    rand = np.random.RandomState(rseed)
    
    arrival_times = np.asarray(arrival_times)
    passenger_times = arrival_times.max() * rand.rand(n_passengers)

    # find the index of the next bus for each simulated passenger
    i = np.searchsorted(arrival_times, passenger_times, side='right')

    return arrival_times[i] - passenger_times

# print vehicles in friendly times
for vehicle in ttc_list:
      times = 0
      for v in vehicle["vehicles"]:
        if v["heading"] > 300:
          times += 1
      time = datetime.datetime.fromtimestamp(int(dict(vehicle)["vtime"]) / 1000)
      for i in range(times):
          print(time, int(dict(vehicle)["vtime"]))
# get experenced vs expected avg waiting times

difference = [0]
prev = 1541710800211 # TODO - shouldn't hardcode first val
current = 0
arrival_times = []
for i in range(1, len(ttc_list)):
    times = 0
    for v in ttc_list[i]["vehicles"]:
        if v["heading"] > 300:
            times += 1
            current = int(dict(ttc_list[i])["vtime"])
            arrival_times.append(current / 60000) 
    time = datetime.datetime.fromtimestamp(int(dict(ttc_list[i])["vtime"]) / 1000)
    for j in range(times):
        if j >= 1:
            difference.append(0)
        else:
            difference.append((current - prev) / 60000)
        print(time, difference[-1])
        prev = current
sum_squares = 0
sum = 0
count = 0
sum_squares_difference = []
for i in range(len(difference)):
  sum += difference[i]
  count += 1
  sum_squares_difference.append(difference[i]**2)
for i in range(len(sum_squares_difference)):
  sum_squares += sum_squares_difference[i]

expected = sum / count
print(sum)
actual = sum_squares / (2*sum)
print(count)
print("expected: ", expected/2)
print("actually experienced by avg customer", actual)

bus_arrival_times = difference
intervals = np.diff(arrival_times[:-1])
print(intervals.mean())