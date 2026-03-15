/*
   Licensed to the Apache Software Foundation (ASF) under one or more
   contributor license agreements.  See the NOTICE file distributed with
   this work for additional information regarding copyright ownership.
   The ASF licenses this file to You under the Apache License, Version 2.0
   (the "License"); you may not use this file except in compliance with
   the License.  You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
*/
$(document).ready(function() {

    $(".click-title").mouseenter( function(    e){
        e.preventDefault();
        this.style.cursor="pointer";
    });
    $(".click-title").mousedown( function(event){
        event.preventDefault();
    });

    // Ugly code while this script is shared among several pages
    try{
        refreshHitsPerSecond(true);
    } catch(e){}
    try{
        refreshResponseTimeOverTime(true);
    } catch(e){}
    try{
        refreshResponseTimePercentiles();
    } catch(e){}
});


var responseTimePercentilesInfos = {
        data: {"result": {"minY": 4.0, "minX": 0.0, "maxY": 1088.0, "series": [{"data": [[0.0, 4.0], [0.1, 15.0], [0.2, 18.0], [0.3, 19.0], [0.4, 19.0], [0.5, 20.0], [0.6, 20.0], [0.7, 21.0], [0.8, 21.0], [0.9, 22.0], [1.0, 22.0], [1.1, 22.0], [1.2, 22.0], [1.3, 23.0], [1.4, 23.0], [1.5, 23.0], [1.6, 23.0], [1.7, 23.0], [1.8, 23.0], [1.9, 24.0], [2.0, 24.0], [2.1, 24.0], [2.2, 24.0], [2.3, 24.0], [2.4, 24.0], [2.5, 25.0], [2.6, 25.0], [2.7, 25.0], [2.8, 25.0], [2.9, 25.0], [3.0, 25.0], [3.1, 25.0], [3.2, 25.0], [3.3, 25.0], [3.4, 25.0], [3.5, 26.0], [3.6, 26.0], [3.7, 26.0], [3.8, 26.0], [3.9, 26.0], [4.0, 26.0], [4.1, 26.0], [4.2, 26.0], [4.3, 26.0], [4.4, 26.0], [4.5, 26.0], [4.6, 26.0], [4.7, 27.0], [4.8, 27.0], [4.9, 27.0], [5.0, 27.0], [5.1, 27.0], [5.2, 27.0], [5.3, 27.0], [5.4, 27.0], [5.5, 27.0], [5.6, 27.0], [5.7, 27.0], [5.8, 27.0], [5.9, 27.0], [6.0, 27.0], [6.1, 27.0], [6.2, 27.0], [6.3, 27.0], [6.4, 27.0], [6.5, 28.0], [6.6, 28.0], [6.7, 28.0], [6.8, 28.0], [6.9, 28.0], [7.0, 28.0], [7.1, 28.0], [7.2, 28.0], [7.3, 28.0], [7.4, 28.0], [7.5, 28.0], [7.6, 28.0], [7.7, 28.0], [7.8, 28.0], [7.9, 28.0], [8.0, 28.0], [8.1, 28.0], [8.2, 28.0], [8.3, 28.0], [8.4, 28.0], [8.5, 28.0], [8.6, 28.0], [8.7, 28.0], [8.8, 29.0], [8.9, 29.0], [9.0, 29.0], [9.1, 29.0], [9.2, 29.0], [9.3, 29.0], [9.4, 29.0], [9.5, 29.0], [9.6, 29.0], [9.7, 29.0], [9.8, 29.0], [9.9, 29.0], [10.0, 29.0], [10.1, 29.0], [10.2, 29.0], [10.3, 29.0], [10.4, 29.0], [10.5, 29.0], [10.6, 29.0], [10.7, 29.0], [10.8, 29.0], [10.9, 29.0], [11.0, 29.0], [11.1, 29.0], [11.2, 29.0], [11.3, 29.0], [11.4, 30.0], [11.5, 30.0], [11.6, 30.0], [11.7, 30.0], [11.8, 30.0], [11.9, 30.0], [12.0, 30.0], [12.1, 30.0], [12.2, 30.0], [12.3, 30.0], [12.4, 30.0], [12.5, 30.0], [12.6, 30.0], [12.7, 30.0], [12.8, 30.0], [12.9, 30.0], [13.0, 30.0], [13.1, 30.0], [13.2, 30.0], [13.3, 30.0], [13.4, 30.0], [13.5, 30.0], [13.6, 30.0], [13.7, 30.0], [13.8, 30.0], [13.9, 30.0], [14.0, 30.0], [14.1, 31.0], [14.2, 31.0], [14.3, 31.0], [14.4, 31.0], [14.5, 31.0], [14.6, 31.0], [14.7, 31.0], [14.8, 31.0], [14.9, 31.0], [15.0, 31.0], [15.1, 31.0], [15.2, 31.0], [15.3, 31.0], [15.4, 31.0], [15.5, 31.0], [15.6, 31.0], [15.7, 31.0], [15.8, 31.0], [15.9, 31.0], [16.0, 31.0], [16.1, 31.0], [16.2, 31.0], [16.3, 31.0], [16.4, 31.0], [16.5, 31.0], [16.6, 32.0], [16.7, 32.0], [16.8, 32.0], [16.9, 32.0], [17.0, 32.0], [17.1, 32.0], [17.2, 32.0], [17.3, 32.0], [17.4, 32.0], [17.5, 32.0], [17.6, 32.0], [17.7, 32.0], [17.8, 32.0], [17.9, 32.0], [18.0, 32.0], [18.1, 32.0], [18.2, 32.0], [18.3, 32.0], [18.4, 32.0], [18.5, 32.0], [18.6, 33.0], [18.7, 33.0], [18.8, 33.0], [18.9, 33.0], [19.0, 33.0], [19.1, 33.0], [19.2, 33.0], [19.3, 33.0], [19.4, 33.0], [19.5, 33.0], [19.6, 33.0], [19.7, 33.0], [19.8, 33.0], [19.9, 33.0], [20.0, 33.0], [20.1, 33.0], [20.2, 33.0], [20.3, 33.0], [20.4, 34.0], [20.5, 34.0], [20.6, 34.0], [20.7, 34.0], [20.8, 34.0], [20.9, 34.0], [21.0, 34.0], [21.1, 34.0], [21.2, 34.0], [21.3, 34.0], [21.4, 34.0], [21.5, 34.0], [21.6, 34.0], [21.7, 34.0], [21.8, 34.0], [21.9, 35.0], [22.0, 35.0], [22.1, 35.0], [22.2, 35.0], [22.3, 35.0], [22.4, 35.0], [22.5, 35.0], [22.6, 35.0], [22.7, 35.0], [22.8, 35.0], [22.9, 35.0], [23.0, 35.0], [23.1, 35.0], [23.2, 35.0], [23.3, 36.0], [23.4, 36.0], [23.5, 36.0], [23.6, 36.0], [23.7, 36.0], [23.8, 36.0], [23.9, 36.0], [24.0, 36.0], [24.1, 36.0], [24.2, 36.0], [24.3, 36.0], [24.4, 36.0], [24.5, 36.0], [24.6, 36.0], [24.7, 37.0], [24.8, 37.0], [24.9, 37.0], [25.0, 37.0], [25.1, 37.0], [25.2, 37.0], [25.3, 37.0], [25.4, 37.0], [25.5, 37.0], [25.6, 37.0], [25.7, 37.0], [25.8, 37.0], [25.9, 37.0], [26.0, 38.0], [26.1, 38.0], [26.2, 38.0], [26.3, 38.0], [26.4, 38.0], [26.5, 38.0], [26.6, 38.0], [26.7, 38.0], [26.8, 38.0], [26.9, 38.0], [27.0, 38.0], [27.1, 38.0], [27.2, 39.0], [27.3, 39.0], [27.4, 39.0], [27.5, 39.0], [27.6, 39.0], [27.7, 39.0], [27.8, 39.0], [27.9, 39.0], [28.0, 39.0], [28.1, 39.0], [28.2, 40.0], [28.3, 40.0], [28.4, 40.0], [28.5, 40.0], [28.6, 40.0], [28.7, 40.0], [28.8, 40.0], [28.9, 40.0], [29.0, 40.0], [29.1, 40.0], [29.2, 40.0], [29.3, 41.0], [29.4, 41.0], [29.5, 41.0], [29.6, 41.0], [29.7, 41.0], [29.8, 41.0], [29.9, 41.0], [30.0, 41.0], [30.1, 41.0], [30.2, 42.0], [30.3, 42.0], [30.4, 42.0], [30.5, 42.0], [30.6, 42.0], [30.7, 42.0], [30.8, 42.0], [30.9, 42.0], [31.0, 42.0], [31.1, 43.0], [31.2, 43.0], [31.3, 43.0], [31.4, 43.0], [31.5, 43.0], [31.6, 43.0], [31.7, 43.0], [31.8, 43.0], [31.9, 43.0], [32.0, 44.0], [32.1, 44.0], [32.2, 44.0], [32.3, 44.0], [32.4, 44.0], [32.5, 44.0], [32.6, 44.0], [32.7, 44.0], [32.8, 44.0], [32.9, 45.0], [33.0, 45.0], [33.1, 45.0], [33.2, 45.0], [33.3, 45.0], [33.4, 45.0], [33.5, 45.0], [33.6, 46.0], [33.7, 46.0], [33.8, 46.0], [33.9, 46.0], [34.0, 46.0], [34.1, 46.0], [34.2, 46.0], [34.3, 47.0], [34.4, 47.0], [34.5, 47.0], [34.6, 47.0], [34.7, 47.0], [34.8, 47.0], [34.9, 47.0], [35.0, 47.0], [35.1, 48.0], [35.2, 48.0], [35.3, 48.0], [35.4, 48.0], [35.5, 48.0], [35.6, 48.0], [35.7, 48.0], [35.8, 48.0], [35.9, 49.0], [36.0, 49.0], [36.1, 49.0], [36.2, 49.0], [36.3, 49.0], [36.4, 49.0], [36.5, 49.0], [36.6, 49.0], [36.7, 49.0], [36.8, 50.0], [36.9, 50.0], [37.0, 50.0], [37.1, 50.0], [37.2, 50.0], [37.3, 50.0], [37.4, 50.0], [37.5, 50.0], [37.6, 51.0], [37.7, 51.0], [37.8, 51.0], [37.9, 51.0], [38.0, 51.0], [38.1, 51.0], [38.2, 51.0], [38.3, 51.0], [38.4, 52.0], [38.5, 52.0], [38.6, 52.0], [38.7, 52.0], [38.8, 52.0], [38.9, 52.0], [39.0, 52.0], [39.1, 53.0], [39.2, 53.0], [39.3, 53.0], [39.4, 53.0], [39.5, 53.0], [39.6, 53.0], [39.7, 53.0], [39.8, 53.0], [39.9, 54.0], [40.0, 54.0], [40.1, 54.0], [40.2, 54.0], [40.3, 54.0], [40.4, 54.0], [40.5, 54.0], [40.6, 54.0], [40.7, 55.0], [40.8, 55.0], [40.9, 55.0], [41.0, 55.0], [41.1, 55.0], [41.2, 55.0], [41.3, 55.0], [41.4, 55.0], [41.5, 56.0], [41.6, 56.0], [41.7, 56.0], [41.8, 56.0], [41.9, 56.0], [42.0, 56.0], [42.1, 56.0], [42.2, 56.0], [42.3, 56.0], [42.4, 56.0], [42.5, 57.0], [42.6, 57.0], [42.7, 57.0], [42.8, 57.0], [42.9, 57.0], [43.0, 57.0], [43.1, 57.0], [43.2, 57.0], [43.3, 57.0], [43.4, 58.0], [43.5, 58.0], [43.6, 58.0], [43.7, 58.0], [43.8, 58.0], [43.9, 58.0], [44.0, 58.0], [44.1, 58.0], [44.2, 58.0], [44.3, 58.0], [44.4, 59.0], [44.5, 59.0], [44.6, 59.0], [44.7, 59.0], [44.8, 59.0], [44.9, 59.0], [45.0, 59.0], [45.1, 59.0], [45.2, 59.0], [45.3, 59.0], [45.4, 59.0], [45.5, 59.0], [45.6, 60.0], [45.7, 60.0], [45.8, 60.0], [45.9, 60.0], [46.0, 60.0], [46.1, 60.0], [46.2, 60.0], [46.3, 60.0], [46.4, 60.0], [46.5, 60.0], [46.6, 61.0], [46.7, 61.0], [46.8, 61.0], [46.9, 61.0], [47.0, 61.0], [47.1, 61.0], [47.2, 61.0], [47.3, 61.0], [47.4, 61.0], [47.5, 61.0], [47.6, 62.0], [47.7, 62.0], [47.8, 62.0], [47.9, 62.0], [48.0, 62.0], [48.1, 62.0], [48.2, 62.0], [48.3, 62.0], [48.4, 62.0], [48.5, 62.0], [48.6, 63.0], [48.7, 63.0], [48.8, 63.0], [48.9, 63.0], [49.0, 63.0], [49.1, 63.0], [49.2, 63.0], [49.3, 63.0], [49.4, 63.0], [49.5, 63.0], [49.6, 63.0], [49.7, 64.0], [49.8, 64.0], [49.9, 64.0], [50.0, 64.0], [50.1, 64.0], [50.2, 64.0], [50.3, 64.0], [50.4, 64.0], [50.5, 64.0], [50.6, 64.0], [50.7, 65.0], [50.8, 65.0], [50.9, 65.0], [51.0, 65.0], [51.1, 65.0], [51.2, 65.0], [51.3, 65.0], [51.4, 65.0], [51.5, 65.0], [51.6, 65.0], [51.7, 66.0], [51.8, 66.0], [51.9, 66.0], [52.0, 66.0], [52.1, 66.0], [52.2, 66.0], [52.3, 66.0], [52.4, 66.0], [52.5, 66.0], [52.6, 66.0], [52.7, 66.0], [52.8, 66.0], [52.9, 67.0], [53.0, 67.0], [53.1, 67.0], [53.2, 67.0], [53.3, 67.0], [53.4, 67.0], [53.5, 67.0], [53.6, 67.0], [53.7, 67.0], [53.8, 67.0], [53.9, 67.0], [54.0, 68.0], [54.1, 68.0], [54.2, 68.0], [54.3, 68.0], [54.4, 68.0], [54.5, 68.0], [54.6, 68.0], [54.7, 68.0], [54.8, 68.0], [54.9, 69.0], [55.0, 69.0], [55.1, 69.0], [55.2, 69.0], [55.3, 69.0], [55.4, 69.0], [55.5, 69.0], [55.6, 69.0], [55.7, 70.0], [55.8, 70.0], [55.9, 70.0], [56.0, 70.0], [56.1, 70.0], [56.2, 70.0], [56.3, 70.0], [56.4, 70.0], [56.5, 70.0], [56.6, 70.0], [56.7, 71.0], [56.8, 71.0], [56.9, 71.0], [57.0, 71.0], [57.1, 71.0], [57.2, 71.0], [57.3, 71.0], [57.4, 71.0], [57.5, 71.0], [57.6, 72.0], [57.7, 72.0], [57.8, 72.0], [57.9, 72.0], [58.0, 72.0], [58.1, 72.0], [58.2, 72.0], [58.3, 72.0], [58.4, 73.0], [58.5, 73.0], [58.6, 73.0], [58.7, 73.0], [58.8, 73.0], [58.9, 73.0], [59.0, 73.0], [59.1, 73.0], [59.2, 73.0], [59.3, 73.0], [59.4, 74.0], [59.5, 74.0], [59.6, 74.0], [59.7, 74.0], [59.8, 74.0], [59.9, 74.0], [60.0, 74.0], [60.1, 74.0], [60.2, 74.0], [60.3, 75.0], [60.4, 75.0], [60.5, 75.0], [60.6, 75.0], [60.7, 75.0], [60.8, 75.0], [60.9, 75.0], [61.0, 75.0], [61.1, 75.0], [61.2, 76.0], [61.3, 76.0], [61.4, 76.0], [61.5, 76.0], [61.6, 76.0], [61.7, 76.0], [61.8, 76.0], [61.9, 76.0], [62.0, 76.0], [62.1, 77.0], [62.2, 77.0], [62.3, 77.0], [62.4, 77.0], [62.5, 77.0], [62.6, 77.0], [62.7, 77.0], [62.8, 77.0], [62.9, 77.0], [63.0, 78.0], [63.1, 78.0], [63.2, 78.0], [63.3, 78.0], [63.4, 78.0], [63.5, 78.0], [63.6, 78.0], [63.7, 78.0], [63.8, 78.0], [63.9, 79.0], [64.0, 79.0], [64.1, 79.0], [64.2, 79.0], [64.3, 79.0], [64.4, 79.0], [64.5, 79.0], [64.6, 79.0], [64.7, 80.0], [64.8, 80.0], [64.9, 80.0], [65.0, 80.0], [65.1, 80.0], [65.2, 80.0], [65.3, 80.0], [65.4, 80.0], [65.5, 80.0], [65.6, 81.0], [65.7, 81.0], [65.8, 81.0], [65.9, 81.0], [66.0, 81.0], [66.1, 81.0], [66.2, 81.0], [66.3, 81.0], [66.4, 81.0], [66.5, 82.0], [66.6, 82.0], [66.7, 82.0], [66.8, 82.0], [66.9, 82.0], [67.0, 82.0], [67.1, 82.0], [67.2, 82.0], [67.3, 83.0], [67.4, 83.0], [67.5, 83.0], [67.6, 83.0], [67.7, 83.0], [67.8, 83.0], [67.9, 83.0], [68.0, 83.0], [68.1, 84.0], [68.2, 84.0], [68.3, 84.0], [68.4, 84.0], [68.5, 84.0], [68.6, 84.0], [68.7, 85.0], [68.8, 85.0], [68.9, 85.0], [69.0, 85.0], [69.1, 85.0], [69.2, 85.0], [69.3, 85.0], [69.4, 86.0], [69.5, 86.0], [69.6, 86.0], [69.7, 86.0], [69.8, 86.0], [69.9, 86.0], [70.0, 87.0], [70.1, 87.0], [70.2, 87.0], [70.3, 87.0], [70.4, 87.0], [70.5, 87.0], [70.6, 87.0], [70.7, 88.0], [70.8, 88.0], [70.9, 88.0], [71.0, 88.0], [71.1, 88.0], [71.2, 89.0], [71.3, 89.0], [71.4, 89.0], [71.5, 89.0], [71.6, 90.0], [71.7, 90.0], [71.8, 90.0], [71.9, 90.0], [72.0, 90.0], [72.1, 90.0], [72.2, 91.0], [72.3, 91.0], [72.4, 91.0], [72.5, 91.0], [72.6, 92.0], [72.7, 92.0], [72.8, 92.0], [72.9, 92.0], [73.0, 93.0], [73.1, 93.0], [73.2, 93.0], [73.3, 93.0], [73.4, 93.0], [73.5, 94.0], [73.6, 94.0], [73.7, 94.0], [73.8, 94.0], [73.9, 95.0], [74.0, 95.0], [74.1, 95.0], [74.2, 95.0], [74.3, 96.0], [74.4, 96.0], [74.5, 96.0], [74.6, 96.0], [74.7, 96.0], [74.8, 97.0], [74.9, 97.0], [75.0, 97.0], [75.1, 97.0], [75.2, 97.0], [75.3, 98.0], [75.4, 98.0], [75.5, 98.0], [75.6, 98.0], [75.7, 99.0], [75.8, 99.0], [75.9, 99.0], [76.0, 99.0], [76.1, 99.0], [76.2, 100.0], [76.3, 100.0], [76.4, 100.0], [76.5, 100.0], [76.6, 100.0], [76.7, 101.0], [76.8, 101.0], [76.9, 101.0], [77.0, 101.0], [77.1, 102.0], [77.2, 102.0], [77.3, 102.0], [77.4, 103.0], [77.5, 103.0], [77.6, 103.0], [77.7, 103.0], [77.8, 104.0], [77.9, 104.0], [78.0, 104.0], [78.1, 105.0], [78.2, 105.0], [78.3, 106.0], [78.4, 106.0], [78.5, 106.0], [78.6, 107.0], [78.7, 107.0], [78.8, 107.0], [78.9, 108.0], [79.0, 108.0], [79.1, 108.0], [79.2, 109.0], [79.3, 109.0], [79.4, 110.0], [79.5, 110.0], [79.6, 110.0], [79.7, 111.0], [79.8, 111.0], [79.9, 111.0], [80.0, 112.0], [80.1, 112.0], [80.2, 112.0], [80.3, 113.0], [80.4, 113.0], [80.5, 113.0], [80.6, 114.0], [80.7, 114.0], [80.8, 115.0], [80.9, 115.0], [81.0, 115.0], [81.1, 116.0], [81.2, 116.0], [81.3, 117.0], [81.4, 117.0], [81.5, 117.0], [81.6, 118.0], [81.7, 118.0], [81.8, 119.0], [81.9, 119.0], [82.0, 120.0], [82.1, 120.0], [82.2, 120.0], [82.3, 121.0], [82.4, 121.0], [82.5, 122.0], [82.6, 122.0], [82.7, 123.0], [82.8, 124.0], [82.9, 124.0], [83.0, 125.0], [83.1, 125.0], [83.2, 126.0], [83.3, 126.0], [83.4, 127.0], [83.5, 127.0], [83.6, 127.0], [83.7, 128.0], [83.8, 128.0], [83.9, 129.0], [84.0, 129.0], [84.1, 130.0], [84.2, 130.0], [84.3, 131.0], [84.4, 131.0], [84.5, 132.0], [84.6, 132.0], [84.7, 133.0], [84.8, 133.0], [84.9, 134.0], [85.0, 135.0], [85.1, 136.0], [85.2, 136.0], [85.3, 137.0], [85.4, 138.0], [85.5, 139.0], [85.6, 139.0], [85.7, 140.0], [85.8, 141.0], [85.9, 142.0], [86.0, 143.0], [86.1, 143.0], [86.2, 144.0], [86.3, 145.0], [86.4, 145.0], [86.5, 146.0], [86.6, 147.0], [86.7, 148.0], [86.8, 148.0], [86.9, 149.0], [87.0, 150.0], [87.1, 151.0], [87.2, 151.0], [87.3, 152.0], [87.4, 153.0], [87.5, 154.0], [87.6, 155.0], [87.7, 156.0], [87.8, 157.0], [87.9, 158.0], [88.0, 160.0], [88.1, 160.0], [88.2, 161.0], [88.3, 162.0], [88.4, 163.0], [88.5, 164.0], [88.6, 164.0], [88.7, 165.0], [88.8, 166.0], [88.9, 167.0], [89.0, 168.0], [89.1, 169.0], [89.2, 170.0], [89.3, 171.0], [89.4, 172.0], [89.5, 173.0], [89.6, 174.0], [89.7, 175.0], [89.8, 176.0], [89.9, 177.0], [90.0, 178.0], [90.1, 179.0], [90.2, 180.0], [90.3, 181.0], [90.4, 182.0], [90.5, 183.0], [90.6, 183.0], [90.7, 184.0], [90.8, 185.0], [90.9, 186.0], [91.0, 187.0], [91.1, 188.0], [91.2, 189.0], [91.3, 190.0], [91.4, 191.0], [91.5, 192.0], [91.6, 194.0], [91.7, 195.0], [91.8, 196.0], [91.9, 197.0], [92.0, 198.0], [92.1, 199.0], [92.2, 200.0], [92.3, 201.0], [92.4, 203.0], [92.5, 205.0], [92.6, 207.0], [92.7, 209.0], [92.8, 210.0], [92.9, 211.0], [93.0, 213.0], [93.1, 214.0], [93.2, 216.0], [93.3, 217.0], [93.4, 219.0], [93.5, 221.0], [93.6, 223.0], [93.7, 225.0], [93.8, 227.0], [93.9, 228.0], [94.0, 230.0], [94.1, 231.0], [94.2, 232.0], [94.3, 234.0], [94.4, 235.0], [94.5, 236.0], [94.6, 237.0], [94.7, 239.0], [94.8, 240.0], [94.9, 242.0], [95.0, 243.0], [95.1, 245.0], [95.2, 246.0], [95.3, 247.0], [95.4, 249.0], [95.5, 251.0], [95.6, 253.0], [95.7, 255.0], [95.8, 257.0], [95.9, 259.0], [96.0, 261.0], [96.1, 263.0], [96.2, 265.0], [96.3, 267.0], [96.4, 270.0], [96.5, 272.0], [96.6, 274.0], [96.7, 276.0], [96.8, 278.0], [96.9, 280.0], [97.0, 282.0], [97.1, 285.0], [97.2, 288.0], [97.3, 291.0], [97.4, 296.0], [97.5, 300.0], [97.6, 303.0], [97.7, 307.0], [97.8, 309.0], [97.9, 312.0], [98.0, 315.0], [98.1, 321.0], [98.2, 328.0], [98.3, 333.0], [98.4, 343.0], [98.5, 348.0], [98.6, 357.0], [98.7, 368.0], [98.8, 380.0], [98.9, 391.0], [99.0, 404.0], [99.1, 420.0], [99.2, 440.0], [99.3, 472.0], [99.4, 514.0], [99.5, 547.0], [99.6, 564.0], [99.7, 688.0], [99.8, 757.0], [99.9, 824.0]], "isOverall": false, "label": "POST /api/v1/beta/translate", "isController": false}], "supportsControllersDiscrimination": true, "maxX": 100.0, "title": "Response Time Percentiles"}},
        getOptions: function() {
            return {
                series: {
                    points: { show: false }
                },
                legend: {
                    noColumns: 2,
                    show: true,
                    container: '#legendResponseTimePercentiles'
                },
                xaxis: {
                    tickDecimals: 1,
                    axisLabel: "Percentiles",
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20,
                },
                yaxis: {
                    axisLabel: "Percentile value in ms",
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20
                },
                grid: {
                    hoverable: true // IMPORTANT! this is needed for tooltip to
                                    // work
                },
                tooltip: true,
                tooltipOpts: {
                    content: "%s : %x.2 percentile was %y ms"
                },
                selection: { mode: "xy" },
            };
        },
        createGraph: function() {
            var data = this.data;
            var dataset = prepareData(data.result.series, $("#choicesResponseTimePercentiles"));
            var options = this.getOptions();
            prepareOptions(options, data);
            $.plot($("#flotResponseTimesPercentiles"), dataset, options);
            // setup overview
            $.plot($("#overviewResponseTimesPercentiles"), dataset, prepareOverviewOptions(options));
        }
};

/**
 * @param elementId Id of element where we display message
 */
function setEmptyGraph(elementId) {
    $(function() {
        $(elementId).text("No graph series with filter="+seriesFilter);
    });
}

// Response times percentiles
function refreshResponseTimePercentiles() {
    var infos = responseTimePercentilesInfos;
    prepareSeries(infos.data);
    if(infos.data.result.series.length == 0) {
        setEmptyGraph("#bodyResponseTimePercentiles");
        return;
    }
    if (isGraph($("#flotResponseTimesPercentiles"))){
        infos.createGraph();
    } else {
        var choiceContainer = $("#choicesResponseTimePercentiles");
        createLegend(choiceContainer, infos);
        infos.createGraph();
        setGraphZoomable("#flotResponseTimesPercentiles", "#overviewResponseTimesPercentiles");
        $('#bodyResponseTimePercentiles .legendColorBox > div').each(function(i){
            $(this).clone().prependTo(choiceContainer.find("li").eq(i));
        });
    }
}

var responseTimeDistributionInfos = {
        data: {"result": {"minY": 20.0, "minX": 0.0, "maxY": 70673.0, "series": [{"data": [[0.0, 70673.0], [300.0, 1354.0], [600.0, 95.0], [700.0, 106.0], [100.0, 14859.0], [200.0, 4980.0], [400.0, 372.0], [800.0, 95.0], [900.0, 26.0], [500.0, 256.0], [1000.0, 20.0]], "isOverall": false, "label": "POST /api/v1/beta/translate", "isController": false}], "supportsControllersDiscrimination": true, "granularity": 100, "maxX": 1000.0, "title": "Response Time Distribution"}},
        getOptions: function() {
            var granularity = this.data.result.granularity;
            return {
                legend: {
                    noColumns: 2,
                    show: true,
                    container: '#legendResponseTimeDistribution'
                },
                xaxis:{
                    axisLabel: "Response times in ms",
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20,
                },
                yaxis: {
                    axisLabel: "Number of responses",
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20,
                },
                bars : {
                    show: true,
                    barWidth: this.data.result.granularity
                },
                grid: {
                    hoverable: true // IMPORTANT! this is needed for tooltip to
                                    // work
                },
                tooltip: true,
                tooltipOpts: {
                    content: function(label, xval, yval, flotItem){
                        return yval + " responses for " + label + " were between " + xval + " and " + (xval + granularity) + " ms";
                    }
                }
            };
        },
        createGraph: function() {
            var data = this.data;
            var options = this.getOptions();
            prepareOptions(options, data);
            $.plot($("#flotResponseTimeDistribution"), prepareData(data.result.series, $("#choicesResponseTimeDistribution")), options);
        }

};

// Response time distribution
function refreshResponseTimeDistribution() {
    var infos = responseTimeDistributionInfos;
    prepareSeries(infos.data);
    if(infos.data.result.series.length == 0) {
        setEmptyGraph("#bodyResponseTimeDistribution");
        return;
    }
    if (isGraph($("#flotResponseTimeDistribution"))){
        infos.createGraph();
    }else{
        var choiceContainer = $("#choicesResponseTimeDistribution");
        createLegend(choiceContainer, infos);
        infos.createGraph();
        $('#footerResponseTimeDistribution .legendColorBox > div').each(function(i){
            $(this).clone().prependTo(choiceContainer.find("li").eq(i));
        });
    }
};


var syntheticResponseTimeDistributionInfos = {
        data: {"result": {"minY": 439.0, "minX": 0.0, "ticks": [[0, "Requests having \nresponse time <= 500ms"], [1, "Requests having \nresponse time > 500ms and <= 1,500ms"], [2, "Requests having \nresponse time > 1,500ms"], [3, "Requests in error"]], "maxY": 53863.0, "series": [{"data": [[0.0, 53863.0]], "color": "#9ACD32", "isOverall": false, "label": "Requests having \nresponse time <= 500ms", "isController": false}, {"data": [[1.0, 439.0]], "color": "yellow", "isOverall": false, "label": "Requests having \nresponse time > 500ms and <= 1,500ms", "isController": false}, {"data": [], "color": "orange", "isOverall": false, "label": "Requests having \nresponse time > 1,500ms", "isController": false}, {"data": [[3.0, 38534.0]], "color": "#FF6347", "isOverall": false, "label": "Requests in error", "isController": false}], "supportsControllersDiscrimination": false, "maxX": 3.0, "title": "Synthetic Response Times Distribution"}},
        getOptions: function() {
            return {
                legend: {
                    noColumns: 2,
                    show: true,
                    container: '#legendSyntheticResponseTimeDistribution'
                },
                xaxis:{
                    axisLabel: "Response times ranges",
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20,
                    tickLength:0,
                    min:-0.5,
                    max:3.5
                },
                yaxis: {
                    axisLabel: "Number of responses",
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20,
                },
                bars : {
                    show: true,
                    align: "center",
                    barWidth: 0.25,
                    fill:.75
                },
                grid: {
                    hoverable: true // IMPORTANT! this is needed for tooltip to
                                    // work
                },
                tooltip: true,
                tooltipOpts: {
                    content: function(label, xval, yval, flotItem){
                        return yval + " " + label;
                    }
                }
            };
        },
        createGraph: function() {
            var data = this.data;
            var options = this.getOptions();
            prepareOptions(options, data);
            options.xaxis.ticks = data.result.ticks;
            $.plot($("#flotSyntheticResponseTimeDistribution"), prepareData(data.result.series, $("#choicesSyntheticResponseTimeDistribution")), options);
        }

};

// Response time distribution
function refreshSyntheticResponseTimeDistribution() {
    var infos = syntheticResponseTimeDistributionInfos;
    prepareSeries(infos.data, true);
    if (isGraph($("#flotSyntheticResponseTimeDistribution"))){
        infos.createGraph();
    }else{
        var choiceContainer = $("#choicesSyntheticResponseTimeDistribution");
        createLegend(choiceContainer, infos);
        infos.createGraph();
        $('#footerSyntheticResponseTimeDistribution .legendColorBox > div').each(function(i){
            $(this).clone().prependTo(choiceContainer.find("li").eq(i));
        });
    }
};

var activeThreadsOverTimeInfos = {
        data: {"result": {"minY": 36.07339857651248, "minX": 1.77361368E12, "maxY": 50.0, "series": [{"data": [[1.7736138E12, 50.0], [1.77361368E12, 36.07339857651248], [1.77361386E12, 49.953657539844684], [1.77361374E12, 50.0]], "isOverall": false, "label": "Threads", "isController": false}], "supportsControllersDiscrimination": false, "granularity": 60000, "maxX": 1.77361386E12, "title": "Active Threads Over Time"}},
        getOptions: function() {
            return {
                series: {
                    stack: true,
                    lines: {
                        show: true,
                        fill: true
                    },
                    points: {
                        show: true
                    }
                },
                xaxis: {
                    mode: "time",
                    timeformat: getTimeFormat(this.data.result.granularity),
                    axisLabel: getElapsedTimeLabel(this.data.result.granularity),
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20,
                },
                yaxis: {
                    axisLabel: "Number of active threads",
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20
                },
                legend: {
                    noColumns: 6,
                    show: true,
                    container: '#legendActiveThreadsOverTime'
                },
                grid: {
                    hoverable: true // IMPORTANT! this is needed for tooltip to
                                    // work
                },
                selection: {
                    mode: 'xy'
                },
                tooltip: true,
                tooltipOpts: {
                    content: "%s : At %x there were %y active threads"
                }
            };
        },
        createGraph: function() {
            var data = this.data;
            var dataset = prepareData(data.result.series, $("#choicesActiveThreadsOverTime"));
            var options = this.getOptions();
            prepareOptions(options, data);
            $.plot($("#flotActiveThreadsOverTime"), dataset, options);
            // setup overview
            $.plot($("#overviewActiveThreadsOverTime"), dataset, prepareOverviewOptions(options));
        }
};

// Active Threads Over Time
function refreshActiveThreadsOverTime(fixTimestamps) {
    var infos = activeThreadsOverTimeInfos;
    prepareSeries(infos.data);
    if(fixTimestamps) {
        fixTimeStamps(infos.data.result.series, 7200000);
    }
    if(isGraph($("#flotActiveThreadsOverTime"))) {
        infos.createGraph();
    }else{
        var choiceContainer = $("#choicesActiveThreadsOverTime");
        createLegend(choiceContainer, infos);
        infos.createGraph();
        setGraphZoomable("#flotActiveThreadsOverTime", "#overviewActiveThreadsOverTime");
        $('#footerActiveThreadsOverTime .legendColorBox > div').each(function(i){
            $(this).clone().prependTo(choiceContainer.find("li").eq(i));
        });
    }
};

var timeVsThreadsInfos = {
        data: {"result": {"minY": 60.6984126984127, "minX": 4.0, "maxY": 345.4027777777778, "series": [{"data": [[32.0, 148.12037037037044], [33.0, 297.29333333333324], [34.0, 187.49056603773587], [35.0, 276.3833333333334], [36.0, 345.4027777777778], [37.0, 201.06306306306305], [38.0, 218.47619047619042], [39.0, 135.34337349397586], [40.0, 170.30327868852459], [41.0, 220.11864406779665], [42.0, 152.45138888888889], [43.0, 186.41610738255042], [44.0, 192.99115044247785], [45.0, 212.7162162162161], [46.0, 164.3976608187135], [47.0, 192.6830985915493], [48.0, 157.64327485380124], [49.0, 218.96774193548384], [50.0, 83.22605329185764], [4.0, 122.75], [5.0, 148.0], [6.0, 81.97142857142856], [7.0, 60.6984126984127], [8.0, 81.25000000000001], [9.0, 63.474358974358964], [10.0, 72.64935064935068], [11.0, 72.1084337349398], [12.0, 85.1882352941176], [13.0, 84.59090909090908], [14.0, 114.91954022988506], [15.0, 89.05000000000007], [16.0, 88.87628865979381], [17.0, 84.41739130434783], [18.0, 176.4821428571428], [19.0, 99.55555555555553], [20.0, 102.24218750000003], [21.0, 120.18811881188118], [22.0, 113.4424778761062], [23.0, 96.35555555555553], [24.0, 121.64347826086951], [25.0, 103.91176470588232], [26.0, 126.00000000000001], [27.0, 130.13934426229505], [28.0, 155.6315789473684], [29.0, 170.42857142857147], [30.0, 109.49710982658961], [31.0, 199.6279069767442]], "isOverall": false, "label": "POST /api/v1/beta/translate", "isController": false}, {"data": [[48.97609763453881, 86.5651148261435]], "isOverall": false, "label": "POST /api/v1/beta/translate-Aggregated", "isController": false}], "supportsControllersDiscrimination": true, "maxX": 50.0, "title": "Time VS Threads"}},
        getOptions: function() {
            return {
                series: {
                    lines: {
                        show: true
                    },
                    points: {
                        show: true
                    }
                },
                xaxis: {
                    axisLabel: "Number of active threads",
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20,
                },
                yaxis: {
                    axisLabel: "Average response times in ms",
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20
                },
                legend: { noColumns: 2,show: true, container: '#legendTimeVsThreads' },
                selection: {
                    mode: 'xy'
                },
                grid: {
                    hoverable: true // IMPORTANT! this is needed for tooltip to work
                },
                tooltip: true,
                tooltipOpts: {
                    content: "%s: At %x.2 active threads, Average response time was %y.2 ms"
                }
            };
        },
        createGraph: function() {
            var data = this.data;
            var dataset = prepareData(data.result.series, $("#choicesTimeVsThreads"));
            var options = this.getOptions();
            prepareOptions(options, data);
            $.plot($("#flotTimesVsThreads"), dataset, options);
            // setup overview
            $.plot($("#overviewTimesVsThreads"), dataset, prepareOverviewOptions(options));
        }
};

// Time vs threads
function refreshTimeVsThreads(){
    var infos = timeVsThreadsInfos;
    prepareSeries(infos.data);
    if(infos.data.result.series.length == 0) {
        setEmptyGraph("#bodyTimeVsThreads");
        return;
    }
    if(isGraph($("#flotTimesVsThreads"))){
        infos.createGraph();
    }else{
        var choiceContainer = $("#choicesTimeVsThreads");
        createLegend(choiceContainer, infos);
        infos.createGraph();
        setGraphZoomable("#flotTimesVsThreads", "#overviewTimesVsThreads");
        $('#footerTimeVsThreads .legendColorBox > div').each(function(i){
            $(this).clone().prependTo(choiceContainer.find("li").eq(i));
        });
    }
};

var bytesThroughputOverTimeInfos = {
        data : {"result": {"minY": 45297.2, "minX": 1.77361368E12, "maxY": 473593.2, "series": [{"data": [[1.7736138E12, 206836.85], [1.77361368E12, 45297.2], [1.77361386E12, 77896.16666666667], [1.77361374E12, 157364.78333333333]], "isOverall": false, "label": "Bytes received per second", "isController": false}, {"data": [[1.7736138E12, 473593.2], [1.77361368E12, 83625.6], [1.77361386E12, 303428.0], [1.77361374E12, 290519.6]], "isOverall": false, "label": "Bytes sent per second", "isController": false}], "supportsControllersDiscrimination": false, "granularity": 60000, "maxX": 1.77361386E12, "title": "Bytes Throughput Over Time"}},
        getOptions : function(){
            return {
                series: {
                    lines: {
                        show: true
                    },
                    points: {
                        show: true
                    }
                },
                xaxis: {
                    mode: "time",
                    timeformat: getTimeFormat(this.data.result.granularity),
                    axisLabel: getElapsedTimeLabel(this.data.result.granularity) ,
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20,
                },
                yaxis: {
                    axisLabel: "Bytes / sec",
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20,
                },
                legend: {
                    noColumns: 2,
                    show: true,
                    container: '#legendBytesThroughputOverTime'
                },
                selection: {
                    mode: "xy"
                },
                grid: {
                    hoverable: true // IMPORTANT! this is needed for tooltip to
                                    // work
                },
                tooltip: true,
                tooltipOpts: {
                    content: "%s at %x was %y"
                }
            };
        },
        createGraph : function() {
            var data = this.data;
            var dataset = prepareData(data.result.series, $("#choicesBytesThroughputOverTime"));
            var options = this.getOptions();
            prepareOptions(options, data);
            $.plot($("#flotBytesThroughputOverTime"), dataset, options);
            // setup overview
            $.plot($("#overviewBytesThroughputOverTime"), dataset, prepareOverviewOptions(options));
        }
};

// Bytes throughput Over Time
function refreshBytesThroughputOverTime(fixTimestamps) {
    var infos = bytesThroughputOverTimeInfos;
    prepareSeries(infos.data);
    if(fixTimestamps) {
        fixTimeStamps(infos.data.result.series, 7200000);
    }
    if(isGraph($("#flotBytesThroughputOverTime"))){
        infos.createGraph();
    }else{
        var choiceContainer = $("#choicesBytesThroughputOverTime");
        createLegend(choiceContainer, infos);
        infos.createGraph();
        setGraphZoomable("#flotBytesThroughputOverTime", "#overviewBytesThroughputOverTime");
        $('#footerBytesThroughputOverTime .legendColorBox > div').each(function(i){
            $(this).clone().prependTo(choiceContainer.find("li").eq(i));
        });
    }
}

var responseTimesOverTimeInfos = {
        data: {"result": {"minY": 36.9145484266448, "minX": 1.77361368E12, "maxY": 188.66622182680874, "series": [{"data": [[1.7736138E12, 76.2371638781977], [1.77361368E12, 188.66622182680874], [1.77361386E12, 36.9145484266448], [1.77361374E12, 125.86832557941034]], "isOverall": false, "label": "POST /api/v1/beta/translate", "isController": false}], "supportsControllersDiscrimination": true, "granularity": 60000, "maxX": 1.77361386E12, "title": "Response Time Over Time"}},
        getOptions: function(){
            return {
                series: {
                    lines: {
                        show: true
                    },
                    points: {
                        show: true
                    }
                },
                xaxis: {
                    mode: "time",
                    timeformat: getTimeFormat(this.data.result.granularity),
                    axisLabel: getElapsedTimeLabel(this.data.result.granularity),
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20,
                },
                yaxis: {
                    axisLabel: "Average response time in ms",
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20,
                },
                legend: {
                    noColumns: 2,
                    show: true,
                    container: '#legendResponseTimesOverTime'
                },
                selection: {
                    mode: 'xy'
                },
                grid: {
                    hoverable: true // IMPORTANT! this is needed for tooltip to
                                    // work
                },
                tooltip: true,
                tooltipOpts: {
                    content: "%s : at %x Average response time was %y ms"
                }
            };
        },
        createGraph: function() {
            var data = this.data;
            var dataset = prepareData(data.result.series, $("#choicesResponseTimesOverTime"));
            var options = this.getOptions();
            prepareOptions(options, data);
            $.plot($("#flotResponseTimesOverTime"), dataset, options);
            // setup overview
            $.plot($("#overviewResponseTimesOverTime"), dataset, prepareOverviewOptions(options));
        }
};

// Response Times Over Time
function refreshResponseTimeOverTime(fixTimestamps) {
    var infos = responseTimesOverTimeInfos;
    prepareSeries(infos.data);
    if(infos.data.result.series.length == 0) {
        setEmptyGraph("#bodyResponseTimeOverTime");
        return;
    }
    if(fixTimestamps) {
        fixTimeStamps(infos.data.result.series, 7200000);
    }
    if(isGraph($("#flotResponseTimesOverTime"))){
        infos.createGraph();
    }else{
        var choiceContainer = $("#choicesResponseTimesOverTime");
        createLegend(choiceContainer, infos);
        infos.createGraph();
        setGraphZoomable("#flotResponseTimesOverTime", "#overviewResponseTimesOverTime");
        $('#footerResponseTimesOverTime .legendColorBox > div').each(function(i){
            $(this).clone().prependTo(choiceContainer.find("li").eq(i));
        });
    }
};

var latenciesOverTimeInfos = {
        data: {"result": {"minY": 36.91046178994653, "minX": 1.77361368E12, "maxY": 188.60854092526682, "series": [{"data": [[1.7736138E12, 76.23101091823136], [1.77361368E12, 188.60854092526682], [1.77361386E12, 36.91046178994653], [1.77361374E12, 125.86013060736752]], "isOverall": false, "label": "POST /api/v1/beta/translate", "isController": false}], "supportsControllersDiscrimination": true, "granularity": 60000, "maxX": 1.77361386E12, "title": "Latencies Over Time"}},
        getOptions: function() {
            return {
                series: {
                    lines: {
                        show: true
                    },
                    points: {
                        show: true
                    }
                },
                xaxis: {
                    mode: "time",
                    timeformat: getTimeFormat(this.data.result.granularity),
                    axisLabel: getElapsedTimeLabel(this.data.result.granularity),
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20,
                },
                yaxis: {
                    axisLabel: "Average response latencies in ms",
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20,
                },
                legend: {
                    noColumns: 2,
                    show: true,
                    container: '#legendLatenciesOverTime'
                },
                selection: {
                    mode: 'xy'
                },
                grid: {
                    hoverable: true // IMPORTANT! this is needed for tooltip to
                                    // work
                },
                tooltip: true,
                tooltipOpts: {
                    content: "%s : at %x Average latency was %y ms"
                }
            };
        },
        createGraph: function () {
            var data = this.data;
            var dataset = prepareData(data.result.series, $("#choicesLatenciesOverTime"));
            var options = this.getOptions();
            prepareOptions(options, data);
            $.plot($("#flotLatenciesOverTime"), dataset, options);
            // setup overview
            $.plot($("#overviewLatenciesOverTime"), dataset, prepareOverviewOptions(options));
        }
};

// Latencies Over Time
function refreshLatenciesOverTime(fixTimestamps) {
    var infos = latenciesOverTimeInfos;
    prepareSeries(infos.data);
    if(infos.data.result.series.length == 0) {
        setEmptyGraph("#bodyLatenciesOverTime");
        return;
    }
    if(fixTimestamps) {
        fixTimeStamps(infos.data.result.series, 7200000);
    }
    if(isGraph($("#flotLatenciesOverTime"))) {
        infos.createGraph();
    }else {
        var choiceContainer = $("#choicesLatenciesOverTime");
        createLegend(choiceContainer, infos);
        infos.createGraph();
        setGraphZoomable("#flotLatenciesOverTime", "#overviewLatenciesOverTime");
        $('#footerLatenciesOverTime .legendColorBox > div').each(function(i){
            $(this).clone().prependTo(choiceContainer.find("li").eq(i));
        });
    }
};

var connectTimeOverTimeInfos = {
        data: {"result": {"minY": 0.0, "minX": 1.77361368E12, "maxY": 0.11847568208778123, "series": [{"data": [[1.7736138E12, 0.002539732411698472], [1.77361368E12, 0.11847568208778123], [1.77361386E12, 0.0], [1.77361374E12, 0.004951128942763237]], "isOverall": false, "label": "POST /api/v1/beta/translate", "isController": false}], "supportsControllersDiscrimination": true, "granularity": 60000, "maxX": 1.77361386E12, "title": "Connect Time Over Time"}},
        getOptions: function() {
            return {
                series: {
                    lines: {
                        show: true
                    },
                    points: {
                        show: true
                    }
                },
                xaxis: {
                    mode: "time",
                    timeformat: getTimeFormat(this.data.result.granularity),
                    axisLabel: getConnectTimeLabel(this.data.result.granularity),
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20,
                },
                yaxis: {
                    axisLabel: "Average Connect Time in ms",
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20,
                },
                legend: {
                    noColumns: 2,
                    show: true,
                    container: '#legendConnectTimeOverTime'
                },
                selection: {
                    mode: 'xy'
                },
                grid: {
                    hoverable: true // IMPORTANT! this is needed for tooltip to
                                    // work
                },
                tooltip: true,
                tooltipOpts: {
                    content: "%s : at %x Average connect time was %y ms"
                }
            };
        },
        createGraph: function () {
            var data = this.data;
            var dataset = prepareData(data.result.series, $("#choicesConnectTimeOverTime"));
            var options = this.getOptions();
            prepareOptions(options, data);
            $.plot($("#flotConnectTimeOverTime"), dataset, options);
            // setup overview
            $.plot($("#overviewConnectTimeOverTime"), dataset, prepareOverviewOptions(options));
        }
};

// Connect Time Over Time
function refreshConnectTimeOverTime(fixTimestamps) {
    var infos = connectTimeOverTimeInfos;
    prepareSeries(infos.data);
    if(infos.data.result.series.length == 0) {
        setEmptyGraph("#bodyConnectTimeOverTime");
        return;
    }
    if(fixTimestamps) {
        fixTimeStamps(infos.data.result.series, 7200000);
    }
    if(isGraph($("#flotConnectTimeOverTime"))) {
        infos.createGraph();
    }else {
        var choiceContainer = $("#choicesConnectTimeOverTime");
        createLegend(choiceContainer, infos);
        infos.createGraph();
        setGraphZoomable("#flotConnectTimeOverTime", "#overviewConnectTimeOverTime");
        $('#footerConnectTimeOverTime .legendColorBox > div').each(function(i){
            $(this).clone().prependTo(choiceContainer.find("li").eq(i));
        });
    }
};

var responseTimePercentilesOverTimeInfos = {
        data: {"result": {"minY": 9.0, "minX": 1.77361368E12, "maxY": 1088.0, "series": [{"data": [[1.7736138E12, 1088.0], [1.77361368E12, 844.0], [1.77361374E12, 945.0]], "isOverall": false, "label": "Max", "isController": false}, {"data": [[1.7736138E12, 133.0], [1.77361368E12, 315.0], [1.77361374E12, 212.0]], "isOverall": false, "label": "90th percentile", "isController": false}, {"data": [[1.7736138E12, 348.0], [1.77361368E12, 569.0], [1.77361374E12, 425.0]], "isOverall": false, "label": "99th percentile", "isController": false}, {"data": [[1.7736138E12, 200.0], [1.77361368E12, 364.0], [1.77361374E12, 262.0]], "isOverall": false, "label": "95th percentile", "isController": false}, {"data": [[1.7736138E12, 18.0], [1.77361368E12, 9.0], [1.77361374E12, 42.0]], "isOverall": false, "label": "Min", "isController": false}, {"data": [[1.7736138E12, 66.0], [1.77361368E12, 170.0], [1.77361374E12, 90.0]], "isOverall": false, "label": "Median", "isController": false}], "supportsControllersDiscrimination": false, "granularity": 60000, "maxX": 1.7736138E12, "title": "Response Time Percentiles Over Time (successful requests only)"}},
        getOptions: function() {
            return {
                series: {
                    lines: {
                        show: true,
                        fill: true
                    },
                    points: {
                        show: true
                    }
                },
                xaxis: {
                    mode: "time",
                    timeformat: getTimeFormat(this.data.result.granularity),
                    axisLabel: getElapsedTimeLabel(this.data.result.granularity),
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20,
                },
                yaxis: {
                    axisLabel: "Response Time in ms",
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20,
                },
                legend: {
                    noColumns: 2,
                    show: true,
                    container: '#legendResponseTimePercentilesOverTime'
                },
                selection: {
                    mode: 'xy'
                },
                grid: {
                    hoverable: true // IMPORTANT! this is needed for tooltip to
                                    // work
                },
                tooltip: true,
                tooltipOpts: {
                    content: "%s : at %x Response time was %y ms"
                }
            };
        },
        createGraph: function () {
            var data = this.data;
            var dataset = prepareData(data.result.series, $("#choicesResponseTimePercentilesOverTime"));
            var options = this.getOptions();
            prepareOptions(options, data);
            $.plot($("#flotResponseTimePercentilesOverTime"), dataset, options);
            // setup overview
            $.plot($("#overviewResponseTimePercentilesOverTime"), dataset, prepareOverviewOptions(options));
        }
};

// Response Time Percentiles Over Time
function refreshResponseTimePercentilesOverTime(fixTimestamps) {
    var infos = responseTimePercentilesOverTimeInfos;
    prepareSeries(infos.data);
    if(fixTimestamps) {
        fixTimeStamps(infos.data.result.series, 7200000);
    }
    if(isGraph($("#flotResponseTimePercentilesOverTime"))) {
        infos.createGraph();
    }else {
        var choiceContainer = $("#choicesResponseTimePercentilesOverTime");
        createLegend(choiceContainer, infos);
        infos.createGraph();
        setGraphZoomable("#flotResponseTimePercentilesOverTime", "#overviewResponseTimePercentilesOverTime");
        $('#footerResponseTimePercentilesOverTime .legendColorBox > div').each(function(i){
            $(this).clone().prependTo(choiceContainer.find("li").eq(i));
        });
    }
};


var responseTimeVsRequestInfos = {
    data: {"result": {"minY": 27.0, "minX": 74.0, "maxY": 415.5, "series": [{"data": [[74.0, 65.0], [97.0, 83.0], [101.0, 282.0], [111.0, 84.0], [109.0, 348.0], [130.0, 70.0], [128.0, 277.0], [132.0, 214.0], [135.0, 293.0], [141.0, 83.0], [136.0, 237.0], [137.0, 306.0], [142.0, 48.0], [150.0, 322.5], [149.0, 263.0], [158.0, 184.0], [157.0, 256.0], [162.0, 157.0], [164.0, 271.5], [161.0, 266.0], [160.0, 306.0], [165.0, 327.0], [172.0, 246.0], [183.0, 76.0], [181.0, 99.0], [179.0, 126.0], [180.0, 258.0], [189.0, 194.0], [184.0, 279.5], [187.0, 214.0], [201.0, 126.0], [206.0, 123.5], [204.0, 188.0], [200.0, 200.0], [205.0, 136.0], [213.0, 241.0], [220.0, 95.0], [217.0, 182.0], [216.0, 210.0], [230.0, 150.0], [228.0, 199.0], [224.0, 163.5], [233.0, 122.0], [234.0, 152.5], [238.0, 179.0], [240.0, 200.0], [250.0, 183.5], [249.0, 193.0], [266.0, 161.0], [270.0, 168.0], [269.0, 180.0], [286.0, 157.5], [276.0, 148.0], [303.0, 160.0], [289.0, 199.0], [300.0, 142.0], [316.0, 130.0], [315.0, 59.0], [330.0, 142.0], [323.0, 140.0], [326.0, 131.5], [324.0, 136.5], [343.0, 129.0], [364.0, 115.0], [363.0, 110.0], [359.0, 123.0], [390.0, 112.0], [427.0, 91.0], [436.0, 95.0], [438.0, 117.0], [441.0, 93.0], [448.0, 106.0], [463.0, 96.0], [464.0, 99.0], [473.0, 96.0], [479.0, 92.0], [470.0, 77.0], [471.0, 104.0], [477.0, 86.0], [495.0, 84.0], [493.0, 93.0], [482.0, 61.0], [505.0, 86.0], [499.0, 92.0], [511.0, 77.0], [506.0, 92.0], [496.0, 100.0], [502.0, 94.0], [526.0, 81.0], [523.0, 87.0], [537.0, 74.0], [533.0, 79.0], [536.0, 88.0], [524.0, 78.0], [541.0, 84.0], [517.0, 84.0], [520.0, 64.0], [574.0, 84.0], [565.0, 78.0], [546.0, 84.0], [572.0, 77.0], [547.0, 71.0], [584.0, 81.0], [595.0, 63.0], [583.0, 73.0], [577.0, 72.0], [606.0, 75.0], [614.0, 74.0], [656.0, 63.0], [651.0, 61.0], [661.0, 63.0], [680.0, 68.0], [689.0, 64.0], [700.0, 58.0], [711.0, 59.0], [712.0, 60.0], [733.0, 60.0], [750.0, 65.0], [746.0, 64.0], [742.0, 55.0], [747.0, 61.0], [766.0, 59.0], [737.0, 59.0], [796.0, 60.0], [821.0, 58.0], [977.0, 61.0]], "isOverall": false, "label": "Successes", "isController": false}, {"data": [[603.0, 30.0], [661.0, 27.0], [746.0, 65.0], [750.0, 60.5], [892.0, 46.0], [947.0, 46.0], [977.0, 30.0], [1023.0, 44.0], [1001.0, 40.0], [994.0, 30.0], [1030.0, 32.0], [1085.0, 36.0], [1128.0, 35.0], [1120.0, 42.0], [1092.0, 35.0], [1198.0, 38.0], [1208.0, 37.0], [1219.0, 34.0], [1236.0, 36.0], [1253.0, 35.0], [1275.0, 32.0], [1340.0, 32.0], [1324.0, 30.0], [1285.0, 35.0], [1384.0, 32.0], [1390.0, 30.0], [1344.0, 30.0], [1369.0, 32.0], [1457.0, 31.0], [1493.0, 30.0], [1495.0, 29.0], [1544.0, 29.0], [103.0, 75.0], [142.0, 166.0], [186.0, 415.5], [308.0, 93.5], [424.0, 77.0]], "isOverall": false, "label": "Failures", "isController": false}], "supportsControllersDiscrimination": false, "granularity": 1000, "maxX": 1544.0, "title": "Response Time Vs Request"}},
    getOptions: function() {
        return {
            series: {
                lines: {
                    show: false
                },
                points: {
                    show: true
                }
            },
            xaxis: {
                axisLabel: "Global number of requests per second",
                axisLabelUseCanvas: true,
                axisLabelFontSizePixels: 12,
                axisLabelFontFamily: 'Verdana, Arial',
                axisLabelPadding: 20,
            },
            yaxis: {
                axisLabel: "Median Response Time in ms",
                axisLabelUseCanvas: true,
                axisLabelFontSizePixels: 12,
                axisLabelFontFamily: 'Verdana, Arial',
                axisLabelPadding: 20,
            },
            legend: {
                noColumns: 2,
                show: true,
                container: '#legendResponseTimeVsRequest'
            },
            selection: {
                mode: 'xy'
            },
            grid: {
                hoverable: true // IMPORTANT! this is needed for tooltip to work
            },
            tooltip: true,
            tooltipOpts: {
                content: "%s : Median response time at %x req/s was %y ms"
            },
            colors: ["#9ACD32", "#FF6347"]
        };
    },
    createGraph: function () {
        var data = this.data;
        var dataset = prepareData(data.result.series, $("#choicesResponseTimeVsRequest"));
        var options = this.getOptions();
        prepareOptions(options, data);
        $.plot($("#flotResponseTimeVsRequest"), dataset, options);
        // setup overview
        $.plot($("#overviewResponseTimeVsRequest"), dataset, prepareOverviewOptions(options));

    }
};

// Response Time vs Request
function refreshResponseTimeVsRequest() {
    var infos = responseTimeVsRequestInfos;
    prepareSeries(infos.data);
    if (isGraph($("#flotResponseTimeVsRequest"))){
        infos.createGraph();
    }else{
        var choiceContainer = $("#choicesResponseTimeVsRequest");
        createLegend(choiceContainer, infos);
        infos.createGraph();
        setGraphZoomable("#flotResponseTimeVsRequest", "#overviewResponseTimeVsRequest");
        $('#footerResponseRimeVsRequest .legendColorBox > div').each(function(i){
            $(this).clone().prependTo(choiceContainer.find("li").eq(i));
        });
    }
};


var latenciesVsRequestInfos = {
    data: {"result": {"minY": 27.0, "minX": 74.0, "maxY": 415.5, "series": [{"data": [[74.0, 65.0], [97.0, 83.0], [101.0, 282.0], [111.0, 84.0], [109.0, 348.0], [130.0, 70.0], [128.0, 277.0], [132.0, 214.0], [135.0, 293.0], [141.0, 83.0], [136.0, 237.0], [137.0, 306.0], [142.0, 48.0], [150.0, 322.5], [149.0, 263.0], [158.0, 184.0], [157.0, 256.0], [162.0, 157.0], [164.0, 271.5], [161.0, 266.0], [160.0, 306.0], [165.0, 327.0], [172.0, 246.0], [183.0, 76.0], [181.0, 99.0], [179.0, 125.0], [180.0, 258.0], [189.0, 194.0], [184.0, 279.5], [187.0, 214.0], [201.0, 126.0], [206.0, 123.5], [204.0, 188.0], [200.0, 200.0], [205.0, 136.0], [213.0, 241.0], [220.0, 95.0], [217.0, 182.0], [216.0, 210.0], [230.0, 150.0], [228.0, 199.0], [224.0, 163.5], [233.0, 122.0], [234.0, 152.5], [238.0, 179.0], [240.0, 200.0], [250.0, 183.5], [249.0, 193.0], [266.0, 161.0], [270.0, 168.0], [269.0, 180.0], [286.0, 157.5], [276.0, 148.0], [303.0, 160.0], [289.0, 199.0], [300.0, 142.0], [316.0, 130.0], [315.0, 59.0], [330.0, 142.0], [323.0, 140.0], [326.0, 131.5], [324.0, 136.5], [343.0, 129.0], [364.0, 115.0], [363.0, 110.0], [359.0, 123.0], [390.0, 112.0], [427.0, 91.0], [436.0, 95.0], [438.0, 117.0], [441.0, 93.0], [448.0, 106.0], [463.0, 96.0], [464.0, 99.0], [473.0, 96.0], [479.0, 92.0], [470.0, 77.0], [471.0, 104.0], [477.0, 86.0], [495.0, 84.0], [493.0, 93.0], [482.0, 61.0], [505.0, 86.0], [499.0, 92.0], [511.0, 77.0], [506.0, 92.0], [496.0, 100.0], [502.0, 94.0], [526.0, 81.0], [523.0, 87.0], [537.0, 74.0], [533.0, 79.0], [536.0, 88.0], [524.0, 78.0], [541.0, 84.0], [517.0, 84.0], [520.0, 64.0], [574.0, 84.0], [565.0, 78.0], [546.0, 84.0], [572.0, 77.0], [547.0, 71.0], [584.0, 81.0], [595.0, 63.0], [583.0, 73.0], [577.0, 72.0], [606.0, 75.0], [614.0, 74.0], [656.0, 63.0], [651.0, 61.0], [661.0, 63.0], [680.0, 68.0], [689.0, 64.0], [700.0, 58.0], [711.0, 59.0], [712.0, 60.0], [733.0, 60.0], [750.0, 65.0], [746.0, 64.0], [742.0, 55.0], [747.0, 61.0], [766.0, 59.0], [737.0, 59.0], [796.0, 60.0], [821.0, 58.0], [977.0, 61.0]], "isOverall": false, "label": "Successes", "isController": false}, {"data": [[603.0, 30.0], [661.0, 27.0], [746.0, 65.0], [750.0, 60.5], [892.0, 46.0], [947.0, 46.0], [977.0, 30.0], [1023.0, 44.0], [1001.0, 40.0], [994.0, 30.0], [1030.0, 32.0], [1085.0, 36.0], [1128.0, 35.0], [1120.0, 42.0], [1092.0, 35.0], [1198.0, 38.0], [1208.0, 37.0], [1219.0, 34.0], [1236.0, 36.0], [1253.0, 35.0], [1275.0, 32.0], [1340.0, 32.0], [1324.0, 30.0], [1285.0, 35.0], [1384.0, 32.0], [1390.0, 30.0], [1344.0, 30.0], [1369.0, 32.0], [1457.0, 31.0], [1493.0, 30.0], [1495.0, 29.0], [1544.0, 29.0], [103.0, 75.0], [142.0, 166.0], [186.0, 415.5], [308.0, 93.5], [424.0, 77.0]], "isOverall": false, "label": "Failures", "isController": false}], "supportsControllersDiscrimination": false, "granularity": 1000, "maxX": 1544.0, "title": "Latencies Vs Request"}},
    getOptions: function() {
        return{
            series: {
                lines: {
                    show: false
                },
                points: {
                    show: true
                }
            },
            xaxis: {
                axisLabel: "Global number of requests per second",
                axisLabelUseCanvas: true,
                axisLabelFontSizePixels: 12,
                axisLabelFontFamily: 'Verdana, Arial',
                axisLabelPadding: 20,
            },
            yaxis: {
                axisLabel: "Median Latency in ms",
                axisLabelUseCanvas: true,
                axisLabelFontSizePixels: 12,
                axisLabelFontFamily: 'Verdana, Arial',
                axisLabelPadding: 20,
            },
            legend: { noColumns: 2,show: true, container: '#legendLatencyVsRequest' },
            selection: {
                mode: 'xy'
            },
            grid: {
                hoverable: true // IMPORTANT! this is needed for tooltip to work
            },
            tooltip: true,
            tooltipOpts: {
                content: "%s : Median Latency time at %x req/s was %y ms"
            },
            colors: ["#9ACD32", "#FF6347"]
        };
    },
    createGraph: function () {
        var data = this.data;
        var dataset = prepareData(data.result.series, $("#choicesLatencyVsRequest"));
        var options = this.getOptions();
        prepareOptions(options, data);
        $.plot($("#flotLatenciesVsRequest"), dataset, options);
        // setup overview
        $.plot($("#overviewLatenciesVsRequest"), dataset, prepareOverviewOptions(options));
    }
};

// Latencies vs Request
function refreshLatenciesVsRequest() {
        var infos = latenciesVsRequestInfos;
        prepareSeries(infos.data);
        if(isGraph($("#flotLatenciesVsRequest"))){
            infos.createGraph();
        }else{
            var choiceContainer = $("#choicesLatencyVsRequest");
            createLegend(choiceContainer, infos);
            infos.createGraph();
            setGraphZoomable("#flotLatenciesVsRequest", "#overviewLatenciesVsRequest");
            $('#footerLatenciesVsRequest .legendColorBox > div').each(function(i){
                $(this).clone().prependTo(choiceContainer.find("li").eq(i));
            });
        }
};

var hitsPerSecondInfos = {
        data: {"result": {"minY": 113.23333333333333, "minX": 1.77361368E12, "maxY": 636.55, "series": [{"data": [[1.7736138E12, 636.55], [1.77361368E12, 113.23333333333333], [1.77361386E12, 407.0], [1.77361374E12, 390.48333333333335]], "isOverall": false, "label": "hitsPerSecond", "isController": false}], "supportsControllersDiscrimination": false, "granularity": 60000, "maxX": 1.77361386E12, "title": "Hits Per Second"}},
        getOptions: function() {
            return {
                series: {
                    lines: {
                        show: true
                    },
                    points: {
                        show: true
                    }
                },
                xaxis: {
                    mode: "time",
                    timeformat: getTimeFormat(this.data.result.granularity),
                    axisLabel: getElapsedTimeLabel(this.data.result.granularity),
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20,
                },
                yaxis: {
                    axisLabel: "Number of hits / sec",
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20
                },
                legend: {
                    noColumns: 2,
                    show: true,
                    container: "#legendHitsPerSecond"
                },
                selection: {
                    mode : 'xy'
                },
                grid: {
                    hoverable: true // IMPORTANT! this is needed for tooltip to
                                    // work
                },
                tooltip: true,
                tooltipOpts: {
                    content: "%s at %x was %y.2 hits/sec"
                }
            };
        },
        createGraph: function createGraph() {
            var data = this.data;
            var dataset = prepareData(data.result.series, $("#choicesHitsPerSecond"));
            var options = this.getOptions();
            prepareOptions(options, data);
            $.plot($("#flotHitsPerSecond"), dataset, options);
            // setup overview
            $.plot($("#overviewHitsPerSecond"), dataset, prepareOverviewOptions(options));
        }
};

// Hits per second
function refreshHitsPerSecond(fixTimestamps) {
    var infos = hitsPerSecondInfos;
    prepareSeries(infos.data);
    if(fixTimestamps) {
        fixTimeStamps(infos.data.result.series, 7200000);
    }
    if (isGraph($("#flotHitsPerSecond"))){
        infos.createGraph();
    }else{
        var choiceContainer = $("#choicesHitsPerSecond");
        createLegend(choiceContainer, infos);
        infos.createGraph();
        setGraphZoomable("#flotHitsPerSecond", "#overviewHitsPerSecond");
        $('#footerHitsPerSecond .legendColorBox > div').each(function(i){
            $(this).clone().prependTo(choiceContainer.find("li").eq(i));
        });
    }
}

var codesPerSecondInfos = {
        data: {"result": {"minY": 112.4, "minX": 1.77361368E12, "maxY": 407.8333333333333, "series": [{"data": [[1.7736138E12, 402.15], [1.77361368E12, 112.4], [1.77361374E12, 390.48333333333335]], "isOverall": false, "label": "200", "isController": false}, {"data": [[1.7736138E12, 234.4], [1.77361386E12, 407.8333333333333]], "isOverall": false, "label": "429", "isController": false}], "supportsControllersDiscrimination": false, "granularity": 60000, "maxX": 1.77361386E12, "title": "Codes Per Second"}},
        getOptions: function(){
            return {
                series: {
                    lines: {
                        show: true
                    },
                    points: {
                        show: true
                    }
                },
                xaxis: {
                    mode: "time",
                    timeformat: getTimeFormat(this.data.result.granularity),
                    axisLabel: getElapsedTimeLabel(this.data.result.granularity),
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20,
                },
                yaxis: {
                    axisLabel: "Number of responses / sec",
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20,
                },
                legend: {
                    noColumns: 2,
                    show: true,
                    container: "#legendCodesPerSecond"
                },
                selection: {
                    mode: 'xy'
                },
                grid: {
                    hoverable: true // IMPORTANT! this is needed for tooltip to
                                    // work
                },
                tooltip: true,
                tooltipOpts: {
                    content: "Number of Response Codes %s at %x was %y.2 responses / sec"
                }
            };
        },
    createGraph: function() {
        var data = this.data;
        var dataset = prepareData(data.result.series, $("#choicesCodesPerSecond"));
        var options = this.getOptions();
        prepareOptions(options, data);
        $.plot($("#flotCodesPerSecond"), dataset, options);
        // setup overview
        $.plot($("#overviewCodesPerSecond"), dataset, prepareOverviewOptions(options));
    }
};

// Codes per second
function refreshCodesPerSecond(fixTimestamps) {
    var infos = codesPerSecondInfos;
    prepareSeries(infos.data);
    if(fixTimestamps) {
        fixTimeStamps(infos.data.result.series, 7200000);
    }
    if(isGraph($("#flotCodesPerSecond"))){
        infos.createGraph();
    }else{
        var choiceContainer = $("#choicesCodesPerSecond");
        createLegend(choiceContainer, infos);
        infos.createGraph();
        setGraphZoomable("#flotCodesPerSecond", "#overviewCodesPerSecond");
        $('#footerCodesPerSecond .legendColorBox > div').each(function(i){
            $(this).clone().prependTo(choiceContainer.find("li").eq(i));
        });
    }
};

var transactionsPerSecondInfos = {
        data: {"result": {"minY": 112.4, "minX": 1.77361368E12, "maxY": 407.8333333333333, "series": [{"data": [[1.7736138E12, 402.15], [1.77361368E12, 112.4], [1.77361374E12, 390.48333333333335]], "isOverall": false, "label": "POST /api/v1/beta/translate-success", "isController": false}, {"data": [[1.7736138E12, 234.4], [1.77361386E12, 407.8333333333333]], "isOverall": false, "label": "POST /api/v1/beta/translate-failure", "isController": false}], "supportsControllersDiscrimination": true, "granularity": 60000, "maxX": 1.77361386E12, "title": "Transactions Per Second"}},
        getOptions: function(){
            return {
                series: {
                    lines: {
                        show: true
                    },
                    points: {
                        show: true
                    }
                },
                xaxis: {
                    mode: "time",
                    timeformat: getTimeFormat(this.data.result.granularity),
                    axisLabel: getElapsedTimeLabel(this.data.result.granularity),
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20,
                },
                yaxis: {
                    axisLabel: "Number of transactions / sec",
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20
                },
                legend: {
                    noColumns: 2,
                    show: true,
                    container: "#legendTransactionsPerSecond"
                },
                selection: {
                    mode: 'xy'
                },
                grid: {
                    hoverable: true // IMPORTANT! this is needed for tooltip to
                                    // work
                },
                tooltip: true,
                tooltipOpts: {
                    content: "%s at %x was %y transactions / sec"
                }
            };
        },
    createGraph: function () {
        var data = this.data;
        var dataset = prepareData(data.result.series, $("#choicesTransactionsPerSecond"));
        var options = this.getOptions();
        prepareOptions(options, data);
        $.plot($("#flotTransactionsPerSecond"), dataset, options);
        // setup overview
        $.plot($("#overviewTransactionsPerSecond"), dataset, prepareOverviewOptions(options));
    }
};

// Transactions per second
function refreshTransactionsPerSecond(fixTimestamps) {
    var infos = transactionsPerSecondInfos;
    prepareSeries(infos.data);
    if(infos.data.result.series.length == 0) {
        setEmptyGraph("#bodyTransactionsPerSecond");
        return;
    }
    if(fixTimestamps) {
        fixTimeStamps(infos.data.result.series, 7200000);
    }
    if(isGraph($("#flotTransactionsPerSecond"))){
        infos.createGraph();
    }else{
        var choiceContainer = $("#choicesTransactionsPerSecond");
        createLegend(choiceContainer, infos);
        infos.createGraph();
        setGraphZoomable("#flotTransactionsPerSecond", "#overviewTransactionsPerSecond");
        $('#footerTransactionsPerSecond .legendColorBox > div').each(function(i){
            $(this).clone().prependTo(choiceContainer.find("li").eq(i));
        });
    }
};

var totalTPSInfos = {
        data: {"result": {"minY": 112.4, "minX": 1.77361368E12, "maxY": 407.8333333333333, "series": [{"data": [[1.7736138E12, 402.15], [1.77361368E12, 112.4], [1.77361374E12, 390.48333333333335]], "isOverall": false, "label": "Transaction-success", "isController": false}, {"data": [[1.7736138E12, 234.4], [1.77361386E12, 407.8333333333333]], "isOverall": false, "label": "Transaction-failure", "isController": false}], "supportsControllersDiscrimination": true, "granularity": 60000, "maxX": 1.77361386E12, "title": "Total Transactions Per Second"}},
        getOptions: function(){
            return {
                series: {
                    lines: {
                        show: true
                    },
                    points: {
                        show: true
                    }
                },
                xaxis: {
                    mode: "time",
                    timeformat: getTimeFormat(this.data.result.granularity),
                    axisLabel: getElapsedTimeLabel(this.data.result.granularity),
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20,
                },
                yaxis: {
                    axisLabel: "Number of transactions / sec",
                    axisLabelUseCanvas: true,
                    axisLabelFontSizePixels: 12,
                    axisLabelFontFamily: 'Verdana, Arial',
                    axisLabelPadding: 20
                },
                legend: {
                    noColumns: 2,
                    show: true,
                    container: "#legendTotalTPS"
                },
                selection: {
                    mode: 'xy'
                },
                grid: {
                    hoverable: true // IMPORTANT! this is needed for tooltip to
                                    // work
                },
                tooltip: true,
                tooltipOpts: {
                    content: "%s at %x was %y transactions / sec"
                },
                colors: ["#9ACD32", "#FF6347"]
            };
        },
    createGraph: function () {
        var data = this.data;
        var dataset = prepareData(data.result.series, $("#choicesTotalTPS"));
        var options = this.getOptions();
        prepareOptions(options, data);
        $.plot($("#flotTotalTPS"), dataset, options);
        // setup overview
        $.plot($("#overviewTotalTPS"), dataset, prepareOverviewOptions(options));
    }
};

// Total Transactions per second
function refreshTotalTPS(fixTimestamps) {
    var infos = totalTPSInfos;
    // We want to ignore seriesFilter
    prepareSeries(infos.data, false, true);
    if(fixTimestamps) {
        fixTimeStamps(infos.data.result.series, 7200000);
    }
    if(isGraph($("#flotTotalTPS"))){
        infos.createGraph();
    }else{
        var choiceContainer = $("#choicesTotalTPS");
        createLegend(choiceContainer, infos);
        infos.createGraph();
        setGraphZoomable("#flotTotalTPS", "#overviewTotalTPS");
        $('#footerTotalTPS .legendColorBox > div').each(function(i){
            $(this).clone().prependTo(choiceContainer.find("li").eq(i));
        });
    }
};

// Collapse the graph matching the specified DOM element depending the collapsed
// status
function collapse(elem, collapsed){
    if(collapsed){
        $(elem).parent().find(".fa-chevron-up").removeClass("fa-chevron-up").addClass("fa-chevron-down");
    } else {
        $(elem).parent().find(".fa-chevron-down").removeClass("fa-chevron-down").addClass("fa-chevron-up");
        if (elem.id == "bodyBytesThroughputOverTime") {
            if (isGraph($(elem).find('.flot-chart-content')) == false) {
                refreshBytesThroughputOverTime(true);
            }
            document.location.href="#bytesThroughputOverTime";
        } else if (elem.id == "bodyLatenciesOverTime") {
            if (isGraph($(elem).find('.flot-chart-content')) == false) {
                refreshLatenciesOverTime(true);
            }
            document.location.href="#latenciesOverTime";
        } else if (elem.id == "bodyCustomGraph") {
            if (isGraph($(elem).find('.flot-chart-content')) == false) {
                refreshCustomGraph(true);
            }
            document.location.href="#responseCustomGraph";
        } else if (elem.id == "bodyConnectTimeOverTime") {
            if (isGraph($(elem).find('.flot-chart-content')) == false) {
                refreshConnectTimeOverTime(true);
            }
            document.location.href="#connectTimeOverTime";
        } else if (elem.id == "bodyResponseTimePercentilesOverTime") {
            if (isGraph($(elem).find('.flot-chart-content')) == false) {
                refreshResponseTimePercentilesOverTime(true);
            }
            document.location.href="#responseTimePercentilesOverTime";
        } else if (elem.id == "bodyResponseTimeDistribution") {
            if (isGraph($(elem).find('.flot-chart-content')) == false) {
                refreshResponseTimeDistribution();
            }
            document.location.href="#responseTimeDistribution" ;
        } else if (elem.id == "bodySyntheticResponseTimeDistribution") {
            if (isGraph($(elem).find('.flot-chart-content')) == false) {
                refreshSyntheticResponseTimeDistribution();
            }
            document.location.href="#syntheticResponseTimeDistribution" ;
        } else if (elem.id == "bodyActiveThreadsOverTime") {
            if (isGraph($(elem).find('.flot-chart-content')) == false) {
                refreshActiveThreadsOverTime(true);
            }
            document.location.href="#activeThreadsOverTime";
        } else if (elem.id == "bodyTimeVsThreads") {
            if (isGraph($(elem).find('.flot-chart-content')) == false) {
                refreshTimeVsThreads();
            }
            document.location.href="#timeVsThreads" ;
        } else if (elem.id == "bodyCodesPerSecond") {
            if (isGraph($(elem).find('.flot-chart-content')) == false) {
                refreshCodesPerSecond(true);
            }
            document.location.href="#codesPerSecond";
        } else if (elem.id == "bodyTransactionsPerSecond") {
            if (isGraph($(elem).find('.flot-chart-content')) == false) {
                refreshTransactionsPerSecond(true);
            }
            document.location.href="#transactionsPerSecond";
        } else if (elem.id == "bodyTotalTPS") {
            if (isGraph($(elem).find('.flot-chart-content')) == false) {
                refreshTotalTPS(true);
            }
            document.location.href="#totalTPS";
        } else if (elem.id == "bodyResponseTimeVsRequest") {
            if (isGraph($(elem).find('.flot-chart-content')) == false) {
                refreshResponseTimeVsRequest();
            }
            document.location.href="#responseTimeVsRequest";
        } else if (elem.id == "bodyLatenciesVsRequest") {
            if (isGraph($(elem).find('.flot-chart-content')) == false) {
                refreshLatenciesVsRequest();
            }
            document.location.href="#latencyVsRequest";
        }
    }
}

/*
 * Activates or deactivates all series of the specified graph (represented by id parameter)
 * depending on checked argument.
 */
function toggleAll(id, checked){
    var placeholder = document.getElementById(id);

    var cases = $(placeholder).find(':checkbox');
    cases.prop('checked', checked);
    $(cases).parent().children().children().toggleClass("legend-disabled", !checked);

    var choiceContainer;
    if ( id == "choicesBytesThroughputOverTime"){
        choiceContainer = $("#choicesBytesThroughputOverTime");
        refreshBytesThroughputOverTime(false);
    } else if(id == "choicesResponseTimesOverTime"){
        choiceContainer = $("#choicesResponseTimesOverTime");
        refreshResponseTimeOverTime(false);
    }else if(id == "choicesResponseCustomGraph"){
        choiceContainer = $("#choicesResponseCustomGraph");
        refreshCustomGraph(false);
    } else if ( id == "choicesLatenciesOverTime"){
        choiceContainer = $("#choicesLatenciesOverTime");
        refreshLatenciesOverTime(false);
    } else if ( id == "choicesConnectTimeOverTime"){
        choiceContainer = $("#choicesConnectTimeOverTime");
        refreshConnectTimeOverTime(false);
    } else if ( id == "choicesResponseTimePercentilesOverTime"){
        choiceContainer = $("#choicesResponseTimePercentilesOverTime");
        refreshResponseTimePercentilesOverTime(false);
    } else if ( id == "choicesResponseTimePercentiles"){
        choiceContainer = $("#choicesResponseTimePercentiles");
        refreshResponseTimePercentiles();
    } else if(id == "choicesActiveThreadsOverTime"){
        choiceContainer = $("#choicesActiveThreadsOverTime");
        refreshActiveThreadsOverTime(false);
    } else if ( id == "choicesTimeVsThreads"){
        choiceContainer = $("#choicesTimeVsThreads");
        refreshTimeVsThreads();
    } else if ( id == "choicesSyntheticResponseTimeDistribution"){
        choiceContainer = $("#choicesSyntheticResponseTimeDistribution");
        refreshSyntheticResponseTimeDistribution();
    } else if ( id == "choicesResponseTimeDistribution"){
        choiceContainer = $("#choicesResponseTimeDistribution");
        refreshResponseTimeDistribution();
    } else if ( id == "choicesHitsPerSecond"){
        choiceContainer = $("#choicesHitsPerSecond");
        refreshHitsPerSecond(false);
    } else if(id == "choicesCodesPerSecond"){
        choiceContainer = $("#choicesCodesPerSecond");
        refreshCodesPerSecond(false);
    } else if ( id == "choicesTransactionsPerSecond"){
        choiceContainer = $("#choicesTransactionsPerSecond");
        refreshTransactionsPerSecond(false);
    } else if ( id == "choicesTotalTPS"){
        choiceContainer = $("#choicesTotalTPS");
        refreshTotalTPS(false);
    } else if ( id == "choicesResponseTimeVsRequest"){
        choiceContainer = $("#choicesResponseTimeVsRequest");
        refreshResponseTimeVsRequest();
    } else if ( id == "choicesLatencyVsRequest"){
        choiceContainer = $("#choicesLatencyVsRequest");
        refreshLatenciesVsRequest();
    }
    var color = checked ? "black" : "#818181";
    if(choiceContainer != null) {
        choiceContainer.find("label").each(function(){
            this.style.color = color;
        });
    }
}

