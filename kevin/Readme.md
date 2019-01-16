"[Bus Route Time Series](https://khmccurdy.github.io/opentransit-metrics/kevin/bus_travel_2.html)" animated map
* Snippets to try in your browser's Console: 

1. `loadBus(Date.now()-20*60e3, Date.now(), "1")` - Loads past 20 minutes of data for route 1 (replace `"1"` with any string found the route dropdown list in the lower corner)
1. `looping = true` - Sets animation to loop instead of stopping at the end of the time series
1. `speedFactor = 30` - Sets animation rate to 30s of data per second of animation time (default is 15)
1. `resetTime()` - Replays current animation from the beginning
