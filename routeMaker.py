import sys
import json
from urllib.request import urlopen
 
 
def mapBox(start, dist):
    mapMaker = [[0.016666, 0.016666, 0.016666, 0.016666], [-0.016666, -0.016666, -0.016666, -0.016666], [2*0.016666, 2*0.016666, 0.016666/2, 0.016666/2], [-2*0.016666, -2*0.016666, 0.016666/-2, 0.016666/-2]]
    mapAlteration =[1,2, 3, 4, 5, 6, dist/6.6, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2]
    mini = 999999999999.9
    for j in range(0, 10):
        for i in range(0,4):
            query = urlopen(f"https://api.mapbox.com/directions/v5/mapbox/walking/{start[0]},{start[1]};{start[0]+mapMaker[i][0] * mapAlteration[j]},{start[1]};{start[0] + mapMaker[i][1] * mapAlteration[j]},{start[1]+mapMaker[i][2] * mapAlteration[j]};{start[0]},{start[1]+mapMaker[i][3] * mapAlteration[j]};{start[0]},{start[1]}?steps=true&geometries=geojson&waypoints=0;4&access_token=pk.eyJ1IjoibW1lbmRpbzIiLCJhIjoiY2t2bWtjcnc3MGJxYjJ3bW56cjJjYWZkOSJ9.F9AITr7LPGEzSbDQ54sEhw")
            jsonVar = json.loads(query.read())
            tempData = jsonVar['routes'][0]
            if abs(tempData['distance']/1609.34-dist)<=mini:
                mini = abs(tempData['distance']/1609.34-dist)
                data = tempData
 
 
    return data, round(data['distance']/1609.34, 2)
 
 
 
if __name__ == '__main__':
    args = sys.argv[1:]
    jsonResults = mapBox((float(args[1]), float(args[0])), float(args[2]))