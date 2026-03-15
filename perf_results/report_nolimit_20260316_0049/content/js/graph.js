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
        data: {"result": {"minY": 26.0, "minX": 0.0, "maxY": 3425.0, "series": [{"data": [[0.0, 26.0], [0.1, 67.0], [0.2, 72.0], [0.3, 76.0], [0.4, 77.0], [0.5, 79.0], [0.6, 80.0], [0.7, 81.0], [0.8, 82.0], [0.9, 83.0], [1.0, 84.0], [1.1, 84.0], [1.2, 85.0], [1.3, 85.0], [1.4, 86.0], [1.5, 87.0], [1.6, 87.0], [1.7, 88.0], [1.8, 88.0], [1.9, 89.0], [2.0, 89.0], [2.1, 90.0], [2.2, 90.0], [2.3, 91.0], [2.4, 91.0], [2.5, 91.0], [2.6, 91.0], [2.7, 92.0], [2.8, 92.0], [2.9, 92.0], [3.0, 93.0], [3.1, 93.0], [3.2, 93.0], [3.3, 94.0], [3.4, 94.0], [3.5, 94.0], [3.6, 94.0], [3.7, 95.0], [3.8, 95.0], [3.9, 95.0], [4.0, 95.0], [4.1, 95.0], [4.2, 96.0], [4.3, 96.0], [4.4, 96.0], [4.5, 97.0], [4.6, 97.0], [4.7, 97.0], [4.8, 97.0], [4.9, 97.0], [5.0, 98.0], [5.1, 98.0], [5.2, 98.0], [5.3, 98.0], [5.4, 98.0], [5.5, 99.0], [5.6, 99.0], [5.7, 99.0], [5.8, 99.0], [5.9, 100.0], [6.0, 100.0], [6.1, 100.0], [6.2, 100.0], [6.3, 100.0], [6.4, 100.0], [6.5, 101.0], [6.6, 101.0], [6.7, 101.0], [6.8, 101.0], [6.9, 101.0], [7.0, 101.0], [7.1, 101.0], [7.2, 102.0], [7.3, 102.0], [7.4, 102.0], [7.5, 102.0], [7.6, 102.0], [7.7, 102.0], [7.8, 103.0], [7.9, 103.0], [8.0, 103.0], [8.1, 104.0], [8.2, 104.0], [8.3, 104.0], [8.4, 104.0], [8.5, 104.0], [8.6, 104.0], [8.7, 105.0], [8.8, 105.0], [8.9, 105.0], [9.0, 105.0], [9.1, 105.0], [9.2, 105.0], [9.3, 106.0], [9.4, 106.0], [9.5, 106.0], [9.6, 106.0], [9.7, 106.0], [9.8, 106.0], [9.9, 106.0], [10.0, 106.0], [10.1, 106.0], [10.2, 107.0], [10.3, 107.0], [10.4, 107.0], [10.5, 107.0], [10.6, 107.0], [10.7, 107.0], [10.8, 107.0], [10.9, 108.0], [11.0, 108.0], [11.1, 108.0], [11.2, 108.0], [11.3, 108.0], [11.4, 108.0], [11.5, 108.0], [11.6, 108.0], [11.7, 108.0], [11.8, 109.0], [11.9, 109.0], [12.0, 109.0], [12.1, 109.0], [12.2, 109.0], [12.3, 109.0], [12.4, 109.0], [12.5, 109.0], [12.6, 110.0], [12.7, 110.0], [12.8, 110.0], [12.9, 110.0], [13.0, 110.0], [13.1, 110.0], [13.2, 110.0], [13.3, 111.0], [13.4, 111.0], [13.5, 111.0], [13.6, 111.0], [13.7, 111.0], [13.8, 111.0], [13.9, 112.0], [14.0, 112.0], [14.1, 112.0], [14.2, 112.0], [14.3, 112.0], [14.4, 112.0], [14.5, 112.0], [14.6, 112.0], [14.7, 112.0], [14.8, 113.0], [14.9, 113.0], [15.0, 113.0], [15.1, 113.0], [15.2, 113.0], [15.3, 113.0], [15.4, 113.0], [15.5, 113.0], [15.6, 114.0], [15.7, 114.0], [15.8, 114.0], [15.9, 114.0], [16.0, 114.0], [16.1, 114.0], [16.2, 114.0], [16.3, 114.0], [16.4, 114.0], [16.5, 115.0], [16.6, 115.0], [16.7, 115.0], [16.8, 115.0], [16.9, 115.0], [17.0, 115.0], [17.1, 115.0], [17.2, 116.0], [17.3, 116.0], [17.4, 116.0], [17.5, 116.0], [17.6, 116.0], [17.7, 116.0], [17.8, 116.0], [17.9, 116.0], [18.0, 116.0], [18.1, 116.0], [18.2, 116.0], [18.3, 117.0], [18.4, 117.0], [18.5, 117.0], [18.6, 117.0], [18.7, 117.0], [18.8, 117.0], [18.9, 117.0], [19.0, 117.0], [19.1, 118.0], [19.2, 118.0], [19.3, 118.0], [19.4, 118.0], [19.5, 118.0], [19.6, 118.0], [19.7, 118.0], [19.8, 119.0], [19.9, 119.0], [20.0, 119.0], [20.1, 119.0], [20.2, 119.0], [20.3, 119.0], [20.4, 119.0], [20.5, 119.0], [20.6, 119.0], [20.7, 120.0], [20.8, 120.0], [20.9, 120.0], [21.0, 120.0], [21.1, 120.0], [21.2, 120.0], [21.3, 120.0], [21.4, 120.0], [21.5, 120.0], [21.6, 121.0], [21.7, 121.0], [21.8, 121.0], [21.9, 121.0], [22.0, 121.0], [22.1, 121.0], [22.2, 121.0], [22.3, 121.0], [22.4, 121.0], [22.5, 122.0], [22.6, 122.0], [22.7, 122.0], [22.8, 122.0], [22.9, 122.0], [23.0, 122.0], [23.1, 122.0], [23.2, 122.0], [23.3, 123.0], [23.4, 123.0], [23.5, 123.0], [23.6, 123.0], [23.7, 123.0], [23.8, 123.0], [23.9, 123.0], [24.0, 123.0], [24.1, 124.0], [24.2, 124.0], [24.3, 124.0], [24.4, 124.0], [24.5, 124.0], [24.6, 124.0], [24.7, 124.0], [24.8, 125.0], [24.9, 125.0], [25.0, 125.0], [25.1, 125.0], [25.2, 125.0], [25.3, 125.0], [25.4, 125.0], [25.5, 125.0], [25.6, 126.0], [25.7, 126.0], [25.8, 126.0], [25.9, 126.0], [26.0, 126.0], [26.1, 126.0], [26.2, 126.0], [26.3, 126.0], [26.4, 126.0], [26.5, 126.0], [26.6, 127.0], [26.7, 127.0], [26.8, 127.0], [26.9, 127.0], [27.0, 127.0], [27.1, 127.0], [27.2, 127.0], [27.3, 127.0], [27.4, 127.0], [27.5, 128.0], [27.6, 128.0], [27.7, 128.0], [27.8, 128.0], [27.9, 128.0], [28.0, 128.0], [28.1, 128.0], [28.2, 128.0], [28.3, 129.0], [28.4, 129.0], [28.5, 129.0], [28.6, 129.0], [28.7, 129.0], [28.8, 129.0], [28.9, 129.0], [29.0, 129.0], [29.1, 130.0], [29.2, 130.0], [29.3, 130.0], [29.4, 130.0], [29.5, 130.0], [29.6, 130.0], [29.7, 130.0], [29.8, 131.0], [29.9, 131.0], [30.0, 131.0], [30.1, 131.0], [30.2, 131.0], [30.3, 131.0], [30.4, 131.0], [30.5, 132.0], [30.6, 132.0], [30.7, 132.0], [30.8, 132.0], [30.9, 132.0], [31.0, 132.0], [31.1, 132.0], [31.2, 132.0], [31.3, 132.0], [31.4, 133.0], [31.5, 133.0], [31.6, 133.0], [31.7, 133.0], [31.8, 133.0], [31.9, 133.0], [32.0, 133.0], [32.1, 134.0], [32.2, 134.0], [32.3, 134.0], [32.4, 134.0], [32.5, 134.0], [32.6, 134.0], [32.7, 134.0], [32.8, 134.0], [32.9, 134.0], [33.0, 135.0], [33.1, 135.0], [33.2, 135.0], [33.3, 135.0], [33.4, 135.0], [33.5, 135.0], [33.6, 135.0], [33.7, 135.0], [33.8, 135.0], [33.9, 136.0], [34.0, 136.0], [34.1, 136.0], [34.2, 136.0], [34.3, 136.0], [34.4, 136.0], [34.5, 136.0], [34.6, 136.0], [34.7, 136.0], [34.8, 137.0], [34.9, 137.0], [35.0, 137.0], [35.1, 137.0], [35.2, 137.0], [35.3, 137.0], [35.4, 137.0], [35.5, 137.0], [35.6, 137.0], [35.7, 138.0], [35.8, 138.0], [35.9, 138.0], [36.0, 138.0], [36.1, 138.0], [36.2, 138.0], [36.3, 138.0], [36.4, 138.0], [36.5, 138.0], [36.6, 139.0], [36.7, 139.0], [36.8, 139.0], [36.9, 139.0], [37.0, 139.0], [37.1, 139.0], [37.2, 139.0], [37.3, 139.0], [37.4, 140.0], [37.5, 140.0], [37.6, 140.0], [37.7, 140.0], [37.8, 140.0], [37.9, 140.0], [38.0, 140.0], [38.1, 140.0], [38.2, 140.0], [38.3, 141.0], [38.4, 141.0], [38.5, 141.0], [38.6, 141.0], [38.7, 141.0], [38.8, 141.0], [38.9, 141.0], [39.0, 141.0], [39.1, 142.0], [39.2, 142.0], [39.3, 142.0], [39.4, 142.0], [39.5, 142.0], [39.6, 142.0], [39.7, 142.0], [39.8, 142.0], [39.9, 143.0], [40.0, 143.0], [40.1, 143.0], [40.2, 143.0], [40.3, 143.0], [40.4, 143.0], [40.5, 143.0], [40.6, 143.0], [40.7, 143.0], [40.8, 144.0], [40.9, 144.0], [41.0, 144.0], [41.1, 144.0], [41.2, 144.0], [41.3, 144.0], [41.4, 144.0], [41.5, 144.0], [41.6, 144.0], [41.7, 145.0], [41.8, 145.0], [41.9, 145.0], [42.0, 145.0], [42.1, 145.0], [42.2, 145.0], [42.3, 145.0], [42.4, 145.0], [42.5, 145.0], [42.6, 146.0], [42.7, 146.0], [42.8, 146.0], [42.9, 146.0], [43.0, 146.0], [43.1, 146.0], [43.2, 146.0], [43.3, 146.0], [43.4, 146.0], [43.5, 147.0], [43.6, 147.0], [43.7, 147.0], [43.8, 147.0], [43.9, 147.0], [44.0, 147.0], [44.1, 147.0], [44.2, 147.0], [44.3, 147.0], [44.4, 148.0], [44.5, 148.0], [44.6, 148.0], [44.7, 148.0], [44.8, 148.0], [44.9, 148.0], [45.0, 148.0], [45.1, 148.0], [45.2, 149.0], [45.3, 149.0], [45.4, 149.0], [45.5, 149.0], [45.6, 149.0], [45.7, 149.0], [45.8, 149.0], [45.9, 150.0], [46.0, 150.0], [46.1, 150.0], [46.2, 150.0], [46.3, 150.0], [46.4, 150.0], [46.5, 150.0], [46.6, 150.0], [46.7, 150.0], [46.8, 151.0], [46.9, 151.0], [47.0, 151.0], [47.1, 151.0], [47.2, 151.0], [47.3, 151.0], [47.4, 151.0], [47.5, 151.0], [47.6, 151.0], [47.7, 152.0], [47.8, 152.0], [47.9, 152.0], [48.0, 152.0], [48.1, 152.0], [48.2, 152.0], [48.3, 152.0], [48.4, 152.0], [48.5, 152.0], [48.6, 153.0], [48.7, 153.0], [48.8, 153.0], [48.9, 153.0], [49.0, 153.0], [49.1, 153.0], [49.2, 153.0], [49.3, 153.0], [49.4, 154.0], [49.5, 154.0], [49.6, 154.0], [49.7, 154.0], [49.8, 154.0], [49.9, 154.0], [50.0, 154.0], [50.1, 154.0], [50.2, 155.0], [50.3, 155.0], [50.4, 155.0], [50.5, 155.0], [50.6, 155.0], [50.7, 155.0], [50.8, 155.0], [50.9, 156.0], [51.0, 156.0], [51.1, 156.0], [51.2, 156.0], [51.3, 156.0], [51.4, 156.0], [51.5, 156.0], [51.6, 156.0], [51.7, 157.0], [51.8, 157.0], [51.9, 157.0], [52.0, 157.0], [52.1, 157.0], [52.2, 157.0], [52.3, 158.0], [52.4, 158.0], [52.5, 158.0], [52.6, 158.0], [52.7, 158.0], [52.8, 158.0], [52.9, 158.0], [53.0, 159.0], [53.1, 159.0], [53.2, 159.0], [53.3, 159.0], [53.4, 159.0], [53.5, 159.0], [53.6, 159.0], [53.7, 160.0], [53.8, 160.0], [53.9, 160.0], [54.0, 160.0], [54.1, 160.0], [54.2, 160.0], [54.3, 161.0], [54.4, 161.0], [54.5, 161.0], [54.6, 161.0], [54.7, 161.0], [54.8, 161.0], [54.9, 162.0], [55.0, 162.0], [55.1, 162.0], [55.2, 162.0], [55.3, 162.0], [55.4, 162.0], [55.5, 162.0], [55.6, 163.0], [55.7, 163.0], [55.8, 163.0], [55.9, 163.0], [56.0, 163.0], [56.1, 163.0], [56.2, 163.0], [56.3, 163.0], [56.4, 163.0], [56.5, 164.0], [56.6, 164.0], [56.7, 164.0], [56.8, 164.0], [56.9, 164.0], [57.0, 164.0], [57.1, 164.0], [57.2, 164.0], [57.3, 165.0], [57.4, 165.0], [57.5, 165.0], [57.6, 165.0], [57.7, 165.0], [57.8, 165.0], [57.9, 165.0], [58.0, 165.0], [58.1, 166.0], [58.2, 166.0], [58.3, 166.0], [58.4, 166.0], [58.5, 166.0], [58.6, 166.0], [58.7, 166.0], [58.8, 166.0], [58.9, 166.0], [59.0, 167.0], [59.1, 167.0], [59.2, 167.0], [59.3, 167.0], [59.4, 167.0], [59.5, 167.0], [59.6, 167.0], [59.7, 167.0], [59.8, 168.0], [59.9, 168.0], [60.0, 168.0], [60.1, 168.0], [60.2, 168.0], [60.3, 168.0], [60.4, 168.0], [60.5, 169.0], [60.6, 169.0], [60.7, 169.0], [60.8, 169.0], [60.9, 169.0], [61.0, 169.0], [61.1, 169.0], [61.2, 169.0], [61.3, 170.0], [61.4, 170.0], [61.5, 170.0], [61.6, 170.0], [61.7, 170.0], [61.8, 170.0], [61.9, 170.0], [62.0, 171.0], [62.1, 171.0], [62.2, 171.0], [62.3, 171.0], [62.4, 171.0], [62.5, 171.0], [62.6, 171.0], [62.7, 172.0], [62.8, 172.0], [62.9, 172.0], [63.0, 172.0], [63.1, 172.0], [63.2, 173.0], [63.3, 173.0], [63.4, 173.0], [63.5, 173.0], [63.6, 173.0], [63.7, 173.0], [63.8, 173.0], [63.9, 174.0], [64.0, 174.0], [64.1, 174.0], [64.2, 174.0], [64.3, 174.0], [64.4, 174.0], [64.5, 175.0], [64.6, 175.0], [64.7, 175.0], [64.8, 175.0], [64.9, 175.0], [65.0, 175.0], [65.1, 175.0], [65.2, 175.0], [65.3, 176.0], [65.4, 176.0], [65.5, 176.0], [65.6, 176.0], [65.7, 176.0], [65.8, 176.0], [65.9, 176.0], [66.0, 177.0], [66.1, 177.0], [66.2, 177.0], [66.3, 177.0], [66.4, 177.0], [66.5, 177.0], [66.6, 177.0], [66.7, 178.0], [66.8, 178.0], [66.9, 178.0], [67.0, 178.0], [67.1, 178.0], [67.2, 179.0], [67.3, 179.0], [67.4, 179.0], [67.5, 179.0], [67.6, 179.0], [67.7, 180.0], [67.8, 180.0], [67.9, 180.0], [68.0, 180.0], [68.1, 180.0], [68.2, 181.0], [68.3, 181.0], [68.4, 181.0], [68.5, 181.0], [68.6, 181.0], [68.7, 181.0], [68.8, 182.0], [68.9, 182.0], [69.0, 182.0], [69.1, 182.0], [69.2, 182.0], [69.3, 182.0], [69.4, 183.0], [69.5, 183.0], [69.6, 183.0], [69.7, 183.0], [69.8, 183.0], [69.9, 184.0], [70.0, 184.0], [70.1, 184.0], [70.2, 184.0], [70.3, 184.0], [70.4, 184.0], [70.5, 185.0], [70.6, 185.0], [70.7, 185.0], [70.8, 185.0], [70.9, 185.0], [71.0, 186.0], [71.1, 186.0], [71.2, 186.0], [71.3, 186.0], [71.4, 186.0], [71.5, 186.0], [71.6, 187.0], [71.7, 187.0], [71.8, 187.0], [71.9, 187.0], [72.0, 187.0], [72.1, 187.0], [72.2, 188.0], [72.3, 188.0], [72.4, 188.0], [72.5, 188.0], [72.6, 188.0], [72.7, 188.0], [72.8, 188.0], [72.9, 189.0], [73.0, 189.0], [73.1, 189.0], [73.2, 189.0], [73.3, 189.0], [73.4, 190.0], [73.5, 190.0], [73.6, 190.0], [73.7, 190.0], [73.8, 190.0], [73.9, 190.0], [74.0, 191.0], [74.1, 191.0], [74.2, 191.0], [74.3, 191.0], [74.4, 191.0], [74.5, 192.0], [74.6, 192.0], [74.7, 192.0], [74.8, 192.0], [74.9, 192.0], [75.0, 192.0], [75.1, 193.0], [75.2, 193.0], [75.3, 193.0], [75.4, 193.0], [75.5, 194.0], [75.6, 194.0], [75.7, 194.0], [75.8, 194.0], [75.9, 194.0], [76.0, 195.0], [76.1, 195.0], [76.2, 195.0], [76.3, 195.0], [76.4, 196.0], [76.5, 196.0], [76.6, 196.0], [76.7, 196.0], [76.8, 196.0], [76.9, 197.0], [77.0, 197.0], [77.1, 197.0], [77.2, 197.0], [77.3, 197.0], [77.4, 198.0], [77.5, 198.0], [77.6, 198.0], [77.7, 198.0], [77.8, 198.0], [77.9, 199.0], [78.0, 199.0], [78.1, 199.0], [78.2, 199.0], [78.3, 200.0], [78.4, 200.0], [78.5, 200.0], [78.6, 200.0], [78.7, 201.0], [78.8, 201.0], [78.9, 201.0], [79.0, 201.0], [79.1, 202.0], [79.2, 202.0], [79.3, 202.0], [79.4, 202.0], [79.5, 202.0], [79.6, 203.0], [79.7, 203.0], [79.8, 203.0], [79.9, 203.0], [80.0, 204.0], [80.1, 204.0], [80.2, 204.0], [80.3, 204.0], [80.4, 204.0], [80.5, 205.0], [80.6, 205.0], [80.7, 205.0], [80.8, 206.0], [80.9, 206.0], [81.0, 206.0], [81.1, 206.0], [81.2, 207.0], [81.3, 207.0], [81.4, 207.0], [81.5, 207.0], [81.6, 208.0], [81.7, 208.0], [81.8, 208.0], [81.9, 209.0], [82.0, 209.0], [82.1, 209.0], [82.2, 210.0], [82.3, 210.0], [82.4, 210.0], [82.5, 211.0], [82.6, 211.0], [82.7, 211.0], [82.8, 212.0], [82.9, 212.0], [83.0, 212.0], [83.1, 213.0], [83.2, 213.0], [83.3, 213.0], [83.4, 213.0], [83.5, 214.0], [83.6, 214.0], [83.7, 215.0], [83.8, 215.0], [83.9, 215.0], [84.0, 216.0], [84.1, 216.0], [84.2, 217.0], [84.3, 217.0], [84.4, 218.0], [84.5, 218.0], [84.6, 218.0], [84.7, 219.0], [84.8, 219.0], [84.9, 220.0], [85.0, 220.0], [85.1, 220.0], [85.2, 221.0], [85.3, 221.0], [85.4, 221.0], [85.5, 222.0], [85.6, 222.0], [85.7, 223.0], [85.8, 223.0], [85.9, 224.0], [86.0, 224.0], [86.1, 225.0], [86.2, 225.0], [86.3, 226.0], [86.4, 226.0], [86.5, 227.0], [86.6, 228.0], [86.7, 228.0], [86.8, 229.0], [86.9, 229.0], [87.0, 230.0], [87.1, 230.0], [87.2, 231.0], [87.3, 232.0], [87.4, 232.0], [87.5, 233.0], [87.6, 233.0], [87.7, 234.0], [87.8, 235.0], [87.9, 236.0], [88.0, 237.0], [88.1, 237.0], [88.2, 238.0], [88.3, 238.0], [88.4, 239.0], [88.5, 240.0], [88.6, 240.0], [88.7, 241.0], [88.8, 241.0], [88.9, 242.0], [89.0, 242.0], [89.1, 243.0], [89.2, 244.0], [89.3, 245.0], [89.4, 245.0], [89.5, 246.0], [89.6, 247.0], [89.7, 247.0], [89.8, 248.0], [89.9, 249.0], [90.0, 249.0], [90.1, 250.0], [90.2, 251.0], [90.3, 253.0], [90.4, 253.0], [90.5, 254.0], [90.6, 255.0], [90.7, 256.0], [90.8, 257.0], [90.9, 257.0], [91.0, 258.0], [91.1, 259.0], [91.2, 260.0], [91.3, 260.0], [91.4, 261.0], [91.5, 262.0], [91.6, 263.0], [91.7, 263.0], [91.8, 265.0], [91.9, 266.0], [92.0, 268.0], [92.1, 269.0], [92.2, 270.0], [92.3, 272.0], [92.4, 273.0], [92.5, 274.0], [92.6, 275.0], [92.7, 276.0], [92.8, 277.0], [92.9, 278.0], [93.0, 280.0], [93.1, 282.0], [93.2, 284.0], [93.3, 286.0], [93.4, 287.0], [93.5, 289.0], [93.6, 290.0], [93.7, 292.0], [93.8, 294.0], [93.9, 296.0], [94.0, 299.0], [94.1, 300.0], [94.2, 301.0], [94.3, 302.0], [94.4, 303.0], [94.5, 304.0], [94.6, 306.0], [94.7, 310.0], [94.8, 312.0], [94.9, 314.0], [95.0, 317.0], [95.1, 321.0], [95.2, 322.0], [95.3, 325.0], [95.4, 329.0], [95.5, 331.0], [95.6, 333.0], [95.7, 337.0], [95.8, 340.0], [95.9, 342.0], [96.0, 343.0], [96.1, 347.0], [96.2, 348.0], [96.3, 351.0], [96.4, 352.0], [96.5, 354.0], [96.6, 355.0], [96.7, 357.0], [96.8, 358.0], [96.9, 360.0], [97.0, 364.0], [97.1, 366.0], [97.2, 370.0], [97.3, 376.0], [97.4, 379.0], [97.5, 381.0], [97.6, 389.0], [97.7, 390.0], [97.8, 392.0], [97.9, 398.0], [98.0, 403.0], [98.1, 409.0], [98.2, 415.0], [98.3, 416.0], [98.4, 419.0], [98.5, 425.0], [98.6, 432.0], [98.7, 442.0], [98.8, 447.0], [98.9, 457.0], [99.0, 470.0], [99.1, 500.0], [99.2, 507.0], [99.3, 516.0], [99.4, 541.0], [99.5, 554.0], [99.6, 603.0], [99.7, 693.0], [99.8, 728.0], [99.9, 2956.0]], "isOverall": false, "label": "POST /api/v1/beta/translate", "isController": false}], "supportsControllersDiscrimination": true, "maxX": 100.0, "title": "Response Time Percentiles"}},
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
        data: {"result": {"minY": 1.0, "minX": 0.0, "maxY": 17029.0, "series": [{"data": [[0.0, 1387.0], [600.0, 35.0], [700.0, 14.0], [900.0, 1.0], [1000.0, 1.0], [1200.0, 1.0], [1300.0, 1.0], [1500.0, 1.0], [100.0, 17029.0], [1600.0, 1.0], [1800.0, 1.0], [2000.0, 1.0], [2100.0, 1.0], [2300.0, 1.0], [2400.0, 1.0], [2600.0, 1.0], [2800.0, 1.0], [2700.0, 1.0], [2900.0, 17.0], [200.0, 3703.0], [3300.0, 7.0], [3400.0, 8.0], [300.0, 910.0], [400.0, 279.0], [500.0, 117.0]], "isOverall": false, "label": "POST /api/v1/beta/translate", "isController": false}], "supportsControllersDiscrimination": true, "granularity": 100, "maxX": 3400.0, "title": "Response Time Distribution"}},
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
        data: {"result": {"minY": 42.0, "minX": 0.0, "ticks": [[0, "Requests having \nresponse time <= 500ms"], [1, "Requests having \nresponse time > 500ms and <= 1,500ms"], [2, "Requests having \nresponse time > 1,500ms"], [3, "Requests in error"]], "maxY": 23310.0, "series": [{"data": [[0.0, 23310.0]], "color": "#9ACD32", "isOverall": false, "label": "Requests having \nresponse time <= 500ms", "isController": false}, {"data": [[1.0, 168.0]], "color": "yellow", "isOverall": false, "label": "Requests having \nresponse time > 500ms and <= 1,500ms", "isController": false}, {"data": [[2.0, 42.0]], "color": "orange", "isOverall": false, "label": "Requests having \nresponse time > 1,500ms", "isController": false}, {"data": [], "color": "#FF6347", "isOverall": false, "label": "Requests in error", "isController": false}], "supportsControllersDiscrimination": false, "maxX": 2.0, "title": "Synthetic Response Times Distribution"}},
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
        data: {"result": {"minY": 48.22235656188197, "minX": 1.77361488E12, "maxY": 49.92289557620301, "series": [{"data": [[1.77361488E12, 48.22235656188197], [1.77361494E12, 49.92289557620301]], "isOverall": false, "label": "Threads", "isController": false}], "supportsControllersDiscrimination": false, "granularity": 60000, "maxX": 1.77361494E12, "title": "Active Threads Over Time"}},
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
        data: {"result": {"minY": 81.3783783783784, "minX": 1.0, "maxY": 2330.9166666666665, "series": [{"data": [[32.0, 150.16666666666666], [36.0, 112.0], [38.0, 109.0], [42.0, 105.66666666666667], [44.0, 142.66666666666666], [46.0, 2330.9166666666665], [47.0, 1993.6585365853666], [48.0, 352.56249999999994], [49.0, 312.20000000000005], [50.0, 172.02935093509356], [8.0, 145.0], [9.0, 143.71428571428572], [15.0, 305.8275862068965], [16.0, 81.3783783783784], [1.0, 146.0], [17.0, 105.66666666666666], [18.0, 95.08571428571432], [19.0, 112.02857142857144], [20.0, 137.4594594594595], [21.0, 91.71428571428572], [22.0, 100.30232558139532], [23.0, 117.61904761904763], [24.0, 135.73913043478257], [25.0, 130.72727272727278], [26.0, 120.78260869565219], [27.0, 92.84444444444445], [28.0, 148.42857142857142], [29.0, 161.44736842105266], [30.0, 168.14285714285714], [31.0, 162.6]], "isOverall": false, "label": "POST /api/v1/beta/translate", "isController": false}, {"data": [[49.26509353741503, 175.84715136054322]], "isOverall": false, "label": "POST /api/v1/beta/translate-Aggregated", "isController": false}], "supportsControllersDiscrimination": true, "maxX": 50.0, "title": "Time VS Threads"}},
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
        data : {"result": {"minY": 61108.23333333333, "minX": 1.77361488E12, "maxY": 178832.8, "series": [{"data": [[1.77361488E12, 61108.23333333333], [1.77361494E12, 96867.76666666666]], "isOverall": false, "label": "Bytes received per second", "isController": false}, {"data": [[1.77361488E12, 112815.2], [1.77361494E12, 178832.8]], "isOverall": false, "label": "Bytes sent per second", "isController": false}], "supportsControllersDiscrimination": false, "granularity": 60000, "maxX": 1.77361494E12, "title": "Bytes Throughput Over Time"}},
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
        data: {"result": {"minY": 162.9292053806679, "minX": 1.77361488E12, "maxY": 196.32446691580526, "series": [{"data": [[1.77361488E12, 196.32446691580526], [1.77361494E12, 162.9292053806679]], "isOverall": false, "label": "POST /api/v1/beta/translate", "isController": false}], "supportsControllersDiscrimination": true, "granularity": 60000, "maxX": 1.77361494E12, "title": "Response Time Over Time"}},
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
        data: {"result": {"minY": 162.92081542088525, "minX": 1.77361488E12, "maxY": 196.27654429544856, "series": [{"data": [[1.77361488E12, 196.27654429544856], [1.77361494E12, 162.92081542088525]], "isOverall": false, "label": "POST /api/v1/beta/translate", "isController": false}], "supportsControllersDiscrimination": true, "granularity": 60000, "maxX": 1.77361494E12, "title": "Latencies Over Time"}},
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
        data: {"result": {"minY": 0.01012342254888367, "minX": 1.77361488E12, "maxY": 0.19784568036931272, "series": [{"data": [[1.77361488E12, 0.19784568036931272], [1.77361494E12, 0.01012342254888367]], "isOverall": false, "label": "POST /api/v1/beta/translate", "isController": false}], "supportsControllersDiscrimination": true, "granularity": 60000, "maxX": 1.77361494E12, "title": "Connect Time Over Time"}},
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
        data: {"result": {"minY": 26.0, "minX": 1.77361488E12, "maxY": 3425.0, "series": [{"data": [[1.77361488E12, 3425.0], [1.77361494E12, 687.0]], "isOverall": false, "label": "Max", "isController": false}, {"data": [[1.77361488E12, 260.0], [1.77361494E12, 245.0]], "isOverall": false, "label": "90th percentile", "isController": false}, {"data": [[1.77361488E12, 509.0], [1.77361494E12, 450.0]], "isOverall": false, "label": "99th percentile", "isController": false}, {"data": [[1.77361488E12, 339.0], [1.77361494E12, 304.0]], "isOverall": false, "label": "95th percentile", "isController": false}, {"data": [[1.77361488E12, 52.0], [1.77361494E12, 26.0]], "isOverall": false, "label": "Min", "isController": false}, {"data": [[1.77361488E12, 167.0], [1.77361494E12, 142.0]], "isOverall": false, "label": "Median", "isController": false}], "supportsControllersDiscrimination": false, "granularity": 60000, "maxX": 1.77361494E12, "title": "Response Time Percentiles Over Time (successful requests only)"}},
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
    data: {"result": {"minY": 97.0, "minX": 18.0, "maxY": 537.0, "series": [{"data": [[18.0, 537.0], [48.0, 171.0], [92.0, 130.5], [124.0, 238.0], [134.0, 286.5], [148.0, 241.5], [161.0, 97.0], [175.0, 175.0], [168.0, 296.0], [181.0, 129.0], [186.0, 113.0], [185.0, 211.0], [199.0, 236.5], [192.0, 235.0], [207.0, 193.0], [211.0, 208.0], [213.0, 217.0], [222.0, 221.5], [223.0, 206.0], [227.0, 202.0], [225.0, 213.0], [228.0, 215.0], [237.0, 154.0], [234.0, 162.0], [239.0, 193.0], [247.0, 193.0], [245.0, 192.0], [244.0, 187.0], [242.0, 186.0], [250.0, 156.0], [248.0, 190.0], [255.0, 174.0], [269.0, 179.0], [265.0, 161.0], [262.0, 185.0], [261.0, 163.0], [256.0, 184.0], [266.0, 194.0], [271.0, 136.0], [267.0, 170.0], [277.0, 168.0], [278.0, 165.0], [275.0, 160.0], [281.0, 176.0], [273.0, 178.0], [287.0, 157.0], [280.0, 167.0], [300.0, 165.0], [298.0, 176.0], [301.0, 166.0], [288.0, 141.0], [307.0, 160.0], [305.0, 144.0], [316.0, 142.0], [325.0, 150.0], [333.0, 149.0], [335.0, 110.0], [323.0, 150.0], [338.0, 136.0], [339.0, 125.5], [347.0, 139.0], [349.0, 142.0], [343.0, 133.0], [367.0, 126.0], [363.0, 120.0], [357.0, 135.0], [368.0, 120.0], [369.0, 117.0], [376.0, 126.0], [397.0, 107.0], [386.0, 124.0], [388.0, 125.0], [402.0, 120.0], [426.0, 111.0], [427.0, 111.0]], "isOverall": false, "label": "Successes", "isController": false}], "supportsControllersDiscrimination": false, "granularity": 1000, "maxX": 427.0, "title": "Response Time Vs Request"}},
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
    data: {"result": {"minY": 97.0, "minX": 18.0, "maxY": 516.0, "series": [{"data": [[18.0, 516.0], [48.0, 171.0], [92.0, 130.5], [124.0, 238.0], [134.0, 286.5], [148.0, 241.5], [161.0, 97.0], [175.0, 175.0], [168.0, 296.0], [181.0, 129.0], [186.0, 113.0], [185.0, 211.0], [199.0, 236.5], [192.0, 235.0], [207.0, 193.0], [211.0, 208.0], [213.0, 217.0], [222.0, 221.5], [223.0, 206.0], [227.0, 202.0], [225.0, 213.0], [228.0, 215.0], [237.0, 154.0], [234.0, 162.0], [239.0, 193.0], [247.0, 193.0], [245.0, 192.0], [244.0, 187.0], [242.0, 186.0], [250.0, 156.0], [248.0, 190.0], [255.0, 174.0], [269.0, 179.0], [265.0, 161.0], [262.0, 185.0], [261.0, 163.0], [256.0, 184.0], [266.0, 194.0], [271.0, 136.0], [267.0, 170.0], [277.0, 167.5], [278.0, 165.0], [275.0, 160.0], [281.0, 176.0], [273.0, 178.0], [287.0, 157.0], [280.0, 167.0], [300.0, 165.0], [298.0, 176.0], [301.0, 166.0], [288.0, 141.0], [307.0, 160.0], [305.0, 144.0], [316.0, 142.0], [325.0, 150.0], [333.0, 149.0], [335.0, 110.0], [323.0, 150.0], [338.0, 136.0], [339.0, 125.0], [347.0, 139.0], [349.0, 142.0], [343.0, 133.0], [367.0, 126.0], [363.0, 120.0], [357.0, 135.0], [368.0, 120.0], [369.0, 117.0], [376.0, 126.0], [397.0, 107.0], [386.0, 124.0], [388.0, 125.0], [402.0, 120.0], [426.0, 111.0], [427.0, 111.0]], "isOverall": false, "label": "Successes", "isController": false}], "supportsControllersDiscrimination": false, "granularity": 1000, "maxX": 427.0, "title": "Latencies Vs Request"}},
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
        data: {"result": {"minY": 152.46666666666667, "minX": 1.77361488E12, "maxY": 239.53333333333333, "series": [{"data": [[1.77361488E12, 152.46666666666667], [1.77361494E12, 239.53333333333333]], "isOverall": false, "label": "hitsPerSecond", "isController": false}], "supportsControllersDiscrimination": false, "granularity": 60000, "maxX": 1.77361494E12, "title": "Hits Per Second"}},
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
        data: {"result": {"minY": 151.63333333333333, "minX": 1.77361488E12, "maxY": 240.36666666666667, "series": [{"data": [[1.77361488E12, 151.63333333333333], [1.77361494E12, 240.36666666666667]], "isOverall": false, "label": "200", "isController": false}], "supportsControllersDiscrimination": false, "granularity": 60000, "maxX": 1.77361494E12, "title": "Codes Per Second"}},
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
        data: {"result": {"minY": 151.63333333333333, "minX": 1.77361488E12, "maxY": 240.36666666666667, "series": [{"data": [[1.77361488E12, 151.63333333333333], [1.77361494E12, 240.36666666666667]], "isOverall": false, "label": "POST /api/v1/beta/translate-success", "isController": false}], "supportsControllersDiscrimination": true, "granularity": 60000, "maxX": 1.77361494E12, "title": "Transactions Per Second"}},
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
        data: {"result": {"minY": 151.63333333333333, "minX": 1.77361488E12, "maxY": 240.36666666666667, "series": [{"data": [[1.77361488E12, 151.63333333333333], [1.77361494E12, 240.36666666666667]], "isOverall": false, "label": "Transaction-success", "isController": false}, {"data": [], "isOverall": false, "label": "Transaction-failure", "isController": false}], "supportsControllersDiscrimination": true, "granularity": 60000, "maxX": 1.77361494E12, "title": "Total Transactions Per Second"}},
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

