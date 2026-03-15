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
        data: {"result": {"minY": 9.0, "minX": 0.0, "maxY": 6241.0, "series": [{"data": [[0.0, 9.0], [0.1, 28.0], [0.2, 51.0], [0.3, 69.0], [0.4, 73.0], [0.5, 74.0], [0.6, 76.0], [0.7, 79.0], [0.8, 83.0], [0.9, 84.0], [1.0, 86.0], [1.1, 88.0], [1.2, 94.0], [1.3, 97.0], [1.4, 100.0], [1.5, 104.0], [1.6, 106.0], [1.7, 108.0], [1.8, 111.0], [1.9, 114.0], [2.0, 117.0], [2.1, 121.0], [2.2, 125.0], [2.3, 130.0], [2.4, 133.0], [2.5, 135.0], [2.6, 143.0], [2.7, 153.0], [2.8, 165.0], [2.9, 174.0], [3.0, 186.0], [3.1, 195.0], [3.2, 198.0], [3.3, 202.0], [3.4, 209.0], [3.5, 212.0], [3.6, 215.0], [3.7, 216.0], [3.8, 219.0], [3.9, 221.0], [4.0, 223.0], [4.1, 224.0], [4.2, 226.0], [4.3, 227.0], [4.4, 229.0], [4.5, 231.0], [4.6, 231.0], [4.7, 232.0], [4.8, 233.0], [4.9, 234.0], [5.0, 235.0], [5.1, 236.0], [5.2, 237.0], [5.3, 237.0], [5.4, 238.0], [5.5, 239.0], [5.6, 240.0], [5.7, 241.0], [5.8, 242.0], [5.9, 244.0], [6.0, 245.0], [6.1, 246.0], [6.2, 247.0], [6.3, 248.0], [6.4, 249.0], [6.5, 249.0], [6.6, 250.0], [6.7, 251.0], [6.8, 251.0], [6.9, 252.0], [7.0, 253.0], [7.1, 254.0], [7.2, 254.0], [7.3, 255.0], [7.4, 255.0], [7.5, 256.0], [7.6, 256.0], [7.7, 257.0], [7.8, 257.0], [7.9, 258.0], [8.0, 258.0], [8.1, 258.0], [8.2, 259.0], [8.3, 259.0], [8.4, 259.0], [8.5, 260.0], [8.6, 260.0], [8.7, 260.0], [8.8, 261.0], [8.9, 261.0], [9.0, 261.0], [9.1, 261.0], [9.2, 262.0], [9.3, 262.0], [9.4, 262.0], [9.5, 263.0], [9.6, 263.0], [9.7, 264.0], [9.8, 264.0], [9.9, 265.0], [10.0, 265.0], [10.1, 265.0], [10.2, 265.0], [10.3, 266.0], [10.4, 266.0], [10.5, 266.0], [10.6, 266.0], [10.7, 267.0], [10.8, 267.0], [10.9, 267.0], [11.0, 268.0], [11.1, 268.0], [11.2, 268.0], [11.3, 269.0], [11.4, 269.0], [11.5, 270.0], [11.6, 270.0], [11.7, 271.0], [11.8, 271.0], [11.9, 271.0], [12.0, 272.0], [12.1, 272.0], [12.2, 272.0], [12.3, 273.0], [12.4, 273.0], [12.5, 273.0], [12.6, 274.0], [12.7, 274.0], [12.8, 275.0], [12.9, 275.0], [13.0, 275.0], [13.1, 276.0], [13.2, 276.0], [13.3, 276.0], [13.4, 276.0], [13.5, 277.0], [13.6, 277.0], [13.7, 277.0], [13.8, 277.0], [13.9, 278.0], [14.0, 278.0], [14.1, 278.0], [14.2, 279.0], [14.3, 279.0], [14.4, 279.0], [14.5, 280.0], [14.6, 280.0], [14.7, 280.0], [14.8, 280.0], [14.9, 280.0], [15.0, 281.0], [15.1, 281.0], [15.2, 281.0], [15.3, 281.0], [15.4, 281.0], [15.5, 281.0], [15.6, 282.0], [15.7, 282.0], [15.8, 282.0], [15.9, 282.0], [16.0, 282.0], [16.1, 282.0], [16.2, 283.0], [16.3, 283.0], [16.4, 283.0], [16.5, 283.0], [16.6, 283.0], [16.7, 283.0], [16.8, 283.0], [16.9, 284.0], [17.0, 284.0], [17.1, 284.0], [17.2, 284.0], [17.3, 284.0], [17.4, 285.0], [17.5, 285.0], [17.6, 285.0], [17.7, 285.0], [17.8, 285.0], [17.9, 285.0], [18.0, 285.0], [18.1, 286.0], [18.2, 286.0], [18.3, 286.0], [18.4, 286.0], [18.5, 286.0], [18.6, 286.0], [18.7, 286.0], [18.8, 287.0], [18.9, 287.0], [19.0, 287.0], [19.1, 287.0], [19.2, 287.0], [19.3, 288.0], [19.4, 288.0], [19.5, 288.0], [19.6, 288.0], [19.7, 288.0], [19.8, 288.0], [19.9, 289.0], [20.0, 289.0], [20.1, 289.0], [20.2, 289.0], [20.3, 289.0], [20.4, 289.0], [20.5, 290.0], [20.6, 290.0], [20.7, 290.0], [20.8, 290.0], [20.9, 290.0], [21.0, 290.0], [21.1, 291.0], [21.2, 291.0], [21.3, 291.0], [21.4, 291.0], [21.5, 291.0], [21.6, 291.0], [21.7, 291.0], [21.8, 292.0], [21.9, 292.0], [22.0, 292.0], [22.1, 292.0], [22.2, 292.0], [22.3, 292.0], [22.4, 292.0], [22.5, 293.0], [22.6, 293.0], [22.7, 293.0], [22.8, 293.0], [22.9, 293.0], [23.0, 293.0], [23.1, 294.0], [23.2, 294.0], [23.3, 294.0], [23.4, 294.0], [23.5, 294.0], [23.6, 294.0], [23.7, 294.0], [23.8, 294.0], [23.9, 295.0], [24.0, 295.0], [24.1, 295.0], [24.2, 295.0], [24.3, 295.0], [24.4, 295.0], [24.5, 295.0], [24.6, 295.0], [24.7, 295.0], [24.8, 296.0], [24.9, 296.0], [25.0, 296.0], [25.1, 296.0], [25.2, 296.0], [25.3, 296.0], [25.4, 296.0], [25.5, 297.0], [25.6, 297.0], [25.7, 297.0], [25.8, 297.0], [25.9, 297.0], [26.0, 297.0], [26.1, 297.0], [26.2, 298.0], [26.3, 298.0], [26.4, 298.0], [26.5, 298.0], [26.6, 298.0], [26.7, 298.0], [26.8, 298.0], [26.9, 298.0], [27.0, 299.0], [27.1, 299.0], [27.2, 299.0], [27.3, 299.0], [27.4, 299.0], [27.5, 299.0], [27.6, 299.0], [27.7, 299.0], [27.8, 300.0], [27.9, 300.0], [28.0, 300.0], [28.1, 300.0], [28.2, 300.0], [28.3, 300.0], [28.4, 300.0], [28.5, 301.0], [28.6, 301.0], [28.7, 301.0], [28.8, 301.0], [28.9, 301.0], [29.0, 301.0], [29.1, 301.0], [29.2, 302.0], [29.3, 302.0], [29.4, 302.0], [29.5, 302.0], [29.6, 302.0], [29.7, 302.0], [29.8, 303.0], [29.9, 303.0], [30.0, 303.0], [30.1, 303.0], [30.2, 303.0], [30.3, 303.0], [30.4, 304.0], [30.5, 304.0], [30.6, 304.0], [30.7, 304.0], [30.8, 305.0], [30.9, 305.0], [31.0, 305.0], [31.1, 305.0], [31.2, 305.0], [31.3, 305.0], [31.4, 305.0], [31.5, 305.0], [31.6, 306.0], [31.7, 306.0], [31.8, 306.0], [31.9, 306.0], [32.0, 306.0], [32.1, 306.0], [32.2, 307.0], [32.3, 307.0], [32.4, 307.0], [32.5, 307.0], [32.6, 307.0], [32.7, 307.0], [32.8, 307.0], [32.9, 308.0], [33.0, 308.0], [33.1, 308.0], [33.2, 308.0], [33.3, 308.0], [33.4, 308.0], [33.5, 309.0], [33.6, 309.0], [33.7, 309.0], [33.8, 309.0], [33.9, 309.0], [34.0, 309.0], [34.1, 309.0], [34.2, 310.0], [34.3, 310.0], [34.4, 310.0], [34.5, 310.0], [34.6, 310.0], [34.7, 310.0], [34.8, 310.0], [34.9, 311.0], [35.0, 311.0], [35.1, 311.0], [35.2, 311.0], [35.3, 311.0], [35.4, 311.0], [35.5, 312.0], [35.6, 312.0], [35.7, 312.0], [35.8, 312.0], [35.9, 312.0], [36.0, 312.0], [36.1, 312.0], [36.2, 313.0], [36.3, 313.0], [36.4, 313.0], [36.5, 313.0], [36.6, 313.0], [36.7, 313.0], [36.8, 313.0], [36.9, 313.0], [37.0, 314.0], [37.1, 314.0], [37.2, 314.0], [37.3, 314.0], [37.4, 314.0], [37.5, 314.0], [37.6, 314.0], [37.7, 314.0], [37.8, 315.0], [37.9, 315.0], [38.0, 315.0], [38.1, 315.0], [38.2, 315.0], [38.3, 315.0], [38.4, 315.0], [38.5, 316.0], [38.6, 316.0], [38.7, 316.0], [38.8, 316.0], [38.9, 316.0], [39.0, 316.0], [39.1, 316.0], [39.2, 316.0], [39.3, 316.0], [39.4, 317.0], [39.5, 317.0], [39.6, 317.0], [39.7, 317.0], [39.8, 317.0], [39.9, 318.0], [40.0, 318.0], [40.1, 318.0], [40.2, 318.0], [40.3, 318.0], [40.4, 318.0], [40.5, 318.0], [40.6, 319.0], [40.7, 319.0], [40.8, 319.0], [40.9, 319.0], [41.0, 319.0], [41.1, 319.0], [41.2, 320.0], [41.3, 320.0], [41.4, 320.0], [41.5, 320.0], [41.6, 320.0], [41.7, 320.0], [41.8, 320.0], [41.9, 321.0], [42.0, 321.0], [42.1, 321.0], [42.2, 321.0], [42.3, 321.0], [42.4, 321.0], [42.5, 321.0], [42.6, 322.0], [42.7, 322.0], [42.8, 322.0], [42.9, 322.0], [43.0, 322.0], [43.1, 323.0], [43.2, 323.0], [43.3, 323.0], [43.4, 323.0], [43.5, 323.0], [43.6, 324.0], [43.7, 324.0], [43.8, 324.0], [43.9, 324.0], [44.0, 324.0], [44.1, 325.0], [44.2, 325.0], [44.3, 325.0], [44.4, 325.0], [44.5, 325.0], [44.6, 326.0], [44.7, 326.0], [44.8, 326.0], [44.9, 326.0], [45.0, 326.0], [45.1, 326.0], [45.2, 326.0], [45.3, 327.0], [45.4, 327.0], [45.5, 327.0], [45.6, 327.0], [45.7, 327.0], [45.8, 327.0], [45.9, 327.0], [46.0, 328.0], [46.1, 328.0], [46.2, 328.0], [46.3, 328.0], [46.4, 328.0], [46.5, 328.0], [46.6, 329.0], [46.7, 329.0], [46.8, 329.0], [46.9, 329.0], [47.0, 329.0], [47.1, 329.0], [47.2, 329.0], [47.3, 330.0], [47.4, 330.0], [47.5, 330.0], [47.6, 330.0], [47.7, 330.0], [47.8, 330.0], [47.9, 330.0], [48.0, 331.0], [48.1, 331.0], [48.2, 331.0], [48.3, 331.0], [48.4, 331.0], [48.5, 331.0], [48.6, 332.0], [48.7, 332.0], [48.8, 332.0], [48.9, 332.0], [49.0, 332.0], [49.1, 333.0], [49.2, 333.0], [49.3, 333.0], [49.4, 333.0], [49.5, 333.0], [49.6, 334.0], [49.7, 334.0], [49.8, 334.0], [49.9, 334.0], [50.0, 334.0], [50.1, 334.0], [50.2, 335.0], [50.3, 335.0], [50.4, 335.0], [50.5, 335.0], [50.6, 335.0], [50.7, 336.0], [50.8, 336.0], [50.9, 336.0], [51.0, 336.0], [51.1, 336.0], [51.2, 336.0], [51.3, 337.0], [51.4, 337.0], [51.5, 337.0], [51.6, 337.0], [51.7, 337.0], [51.8, 338.0], [51.9, 338.0], [52.0, 338.0], [52.1, 338.0], [52.2, 338.0], [52.3, 338.0], [52.4, 339.0], [52.5, 339.0], [52.6, 339.0], [52.7, 339.0], [52.8, 339.0], [52.9, 340.0], [53.0, 340.0], [53.1, 340.0], [53.2, 340.0], [53.3, 340.0], [53.4, 341.0], [53.5, 341.0], [53.6, 341.0], [53.7, 341.0], [53.8, 341.0], [53.9, 341.0], [54.0, 342.0], [54.1, 342.0], [54.2, 342.0], [54.3, 342.0], [54.4, 342.0], [54.5, 343.0], [54.6, 343.0], [54.7, 343.0], [54.8, 343.0], [54.9, 343.0], [55.0, 344.0], [55.1, 344.0], [55.2, 344.0], [55.3, 344.0], [55.4, 344.0], [55.5, 344.0], [55.6, 345.0], [55.7, 345.0], [55.8, 345.0], [55.9, 346.0], [56.0, 346.0], [56.1, 346.0], [56.2, 346.0], [56.3, 347.0], [56.4, 347.0], [56.5, 347.0], [56.6, 347.0], [56.7, 347.0], [56.8, 347.0], [56.9, 348.0], [57.0, 348.0], [57.1, 348.0], [57.2, 348.0], [57.3, 349.0], [57.4, 349.0], [57.5, 349.0], [57.6, 349.0], [57.7, 350.0], [57.8, 350.0], [57.9, 350.0], [58.0, 350.0], [58.1, 350.0], [58.2, 350.0], [58.3, 351.0], [58.4, 351.0], [58.5, 351.0], [58.6, 351.0], [58.7, 352.0], [58.8, 352.0], [58.9, 352.0], [59.0, 352.0], [59.1, 353.0], [59.2, 353.0], [59.3, 353.0], [59.4, 353.0], [59.5, 354.0], [59.6, 354.0], [59.7, 354.0], [59.8, 355.0], [59.9, 355.0], [60.0, 355.0], [60.1, 355.0], [60.2, 356.0], [60.3, 356.0], [60.4, 356.0], [60.5, 356.0], [60.6, 357.0], [60.7, 357.0], [60.8, 357.0], [60.9, 357.0], [61.0, 358.0], [61.1, 358.0], [61.2, 358.0], [61.3, 358.0], [61.4, 358.0], [61.5, 359.0], [61.6, 359.0], [61.7, 359.0], [61.8, 360.0], [61.9, 360.0], [62.0, 360.0], [62.1, 360.0], [62.2, 361.0], [62.3, 361.0], [62.4, 361.0], [62.5, 361.0], [62.6, 362.0], [62.7, 362.0], [62.8, 362.0], [62.9, 362.0], [63.0, 362.0], [63.1, 363.0], [63.2, 363.0], [63.3, 363.0], [63.4, 364.0], [63.5, 364.0], [63.6, 364.0], [63.7, 364.0], [63.8, 364.0], [63.9, 365.0], [64.0, 365.0], [64.1, 365.0], [64.2, 366.0], [64.3, 366.0], [64.4, 366.0], [64.5, 366.0], [64.6, 367.0], [64.7, 367.0], [64.8, 368.0], [64.9, 368.0], [65.0, 368.0], [65.1, 368.0], [65.2, 369.0], [65.3, 369.0], [65.4, 369.0], [65.5, 369.0], [65.6, 370.0], [65.7, 370.0], [65.8, 370.0], [65.9, 370.0], [66.0, 371.0], [66.1, 371.0], [66.2, 372.0], [66.3, 372.0], [66.4, 372.0], [66.5, 373.0], [66.6, 373.0], [66.7, 373.0], [66.8, 374.0], [66.9, 374.0], [67.0, 375.0], [67.1, 375.0], [67.2, 375.0], [67.3, 375.0], [67.4, 376.0], [67.5, 376.0], [67.6, 377.0], [67.7, 377.0], [67.8, 377.0], [67.9, 378.0], [68.0, 378.0], [68.1, 378.0], [68.2, 379.0], [68.3, 379.0], [68.4, 380.0], [68.5, 380.0], [68.6, 380.0], [68.7, 380.0], [68.8, 381.0], [68.9, 381.0], [69.0, 381.0], [69.1, 382.0], [69.2, 382.0], [69.3, 383.0], [69.4, 383.0], [69.5, 384.0], [69.6, 384.0], [69.7, 385.0], [69.8, 385.0], [69.9, 385.0], [70.0, 386.0], [70.1, 386.0], [70.2, 386.0], [70.3, 386.0], [70.4, 387.0], [70.5, 387.0], [70.6, 387.0], [70.7, 388.0], [70.8, 388.0], [70.9, 389.0], [71.0, 389.0], [71.1, 390.0], [71.2, 390.0], [71.3, 391.0], [71.4, 391.0], [71.5, 391.0], [71.6, 392.0], [71.7, 392.0], [71.8, 393.0], [71.9, 393.0], [72.0, 393.0], [72.1, 394.0], [72.2, 394.0], [72.3, 394.0], [72.4, 395.0], [72.5, 395.0], [72.6, 396.0], [72.7, 396.0], [72.8, 396.0], [72.9, 397.0], [73.0, 397.0], [73.1, 398.0], [73.2, 398.0], [73.3, 398.0], [73.4, 399.0], [73.5, 399.0], [73.6, 400.0], [73.7, 400.0], [73.8, 401.0], [73.9, 401.0], [74.0, 402.0], [74.1, 402.0], [74.2, 403.0], [74.3, 404.0], [74.4, 404.0], [74.5, 405.0], [74.6, 405.0], [74.7, 406.0], [74.8, 406.0], [74.9, 407.0], [75.0, 407.0], [75.1, 408.0], [75.2, 409.0], [75.3, 410.0], [75.4, 410.0], [75.5, 411.0], [75.6, 411.0], [75.7, 411.0], [75.8, 412.0], [75.9, 413.0], [76.0, 413.0], [76.1, 414.0], [76.2, 414.0], [76.3, 415.0], [76.4, 415.0], [76.5, 416.0], [76.6, 416.0], [76.7, 417.0], [76.8, 417.0], [76.9, 417.0], [77.0, 418.0], [77.1, 419.0], [77.2, 419.0], [77.3, 420.0], [77.4, 420.0], [77.5, 421.0], [77.6, 421.0], [77.7, 422.0], [77.8, 422.0], [77.9, 423.0], [78.0, 423.0], [78.1, 424.0], [78.2, 425.0], [78.3, 425.0], [78.4, 426.0], [78.5, 426.0], [78.6, 427.0], [78.7, 427.0], [78.8, 428.0], [78.9, 428.0], [79.0, 429.0], [79.1, 430.0], [79.2, 431.0], [79.3, 432.0], [79.4, 433.0], [79.5, 433.0], [79.6, 435.0], [79.7, 436.0], [79.8, 437.0], [79.9, 438.0], [80.0, 440.0], [80.1, 442.0], [80.2, 443.0], [80.3, 444.0], [80.4, 445.0], [80.5, 446.0], [80.6, 448.0], [80.7, 449.0], [80.8, 450.0], [80.9, 451.0], [81.0, 451.0], [81.1, 452.0], [81.2, 453.0], [81.3, 454.0], [81.4, 455.0], [81.5, 457.0], [81.6, 458.0], [81.7, 459.0], [81.8, 459.0], [81.9, 460.0], [82.0, 461.0], [82.1, 462.0], [82.2, 463.0], [82.3, 463.0], [82.4, 464.0], [82.5, 464.0], [82.6, 465.0], [82.7, 467.0], [82.8, 468.0], [82.9, 469.0], [83.0, 470.0], [83.1, 472.0], [83.2, 473.0], [83.3, 474.0], [83.4, 475.0], [83.5, 476.0], [83.6, 477.0], [83.7, 478.0], [83.8, 480.0], [83.9, 481.0], [84.0, 482.0], [84.1, 484.0], [84.2, 486.0], [84.3, 488.0], [84.4, 490.0], [84.5, 491.0], [84.6, 493.0], [84.7, 495.0], [84.8, 495.0], [84.9, 496.0], [85.0, 498.0], [85.1, 500.0], [85.2, 502.0], [85.3, 504.0], [85.4, 506.0], [85.5, 507.0], [85.6, 509.0], [85.7, 511.0], [85.8, 512.0], [85.9, 513.0], [86.0, 514.0], [86.1, 514.0], [86.2, 515.0], [86.3, 516.0], [86.4, 516.0], [86.5, 517.0], [86.6, 518.0], [86.7, 519.0], [86.8, 519.0], [86.9, 520.0], [87.0, 521.0], [87.1, 522.0], [87.2, 523.0], [87.3, 524.0], [87.4, 525.0], [87.5, 525.0], [87.6, 526.0], [87.7, 527.0], [87.8, 528.0], [87.9, 529.0], [88.0, 530.0], [88.1, 532.0], [88.2, 532.0], [88.3, 533.0], [88.4, 534.0], [88.5, 536.0], [88.6, 538.0], [88.7, 540.0], [88.8, 541.0], [88.9, 542.0], [89.0, 543.0], [89.1, 544.0], [89.2, 546.0], [89.3, 547.0], [89.4, 549.0], [89.5, 551.0], [89.6, 553.0], [89.7, 555.0], [89.8, 557.0], [89.9, 558.0], [90.0, 559.0], [90.1, 560.0], [90.2, 561.0], [90.3, 562.0], [90.4, 563.0], [90.5, 565.0], [90.6, 566.0], [90.7, 567.0], [90.8, 569.0], [90.9, 572.0], [91.0, 574.0], [91.1, 575.0], [91.2, 576.0], [91.3, 578.0], [91.4, 581.0], [91.5, 583.0], [91.6, 583.0], [91.7, 584.0], [91.8, 586.0], [91.9, 587.0], [92.0, 588.0], [92.1, 590.0], [92.2, 592.0], [92.3, 594.0], [92.4, 597.0], [92.5, 599.0], [92.6, 602.0], [92.7, 603.0], [92.8, 606.0], [92.9, 609.0], [93.0, 611.0], [93.1, 612.0], [93.2, 614.0], [93.3, 617.0], [93.4, 619.0], [93.5, 622.0], [93.6, 625.0], [93.7, 629.0], [93.8, 633.0], [93.9, 635.0], [94.0, 637.0], [94.1, 640.0], [94.2, 643.0], [94.3, 645.0], [94.4, 651.0], [94.5, 658.0], [94.6, 662.0], [94.7, 664.0], [94.8, 668.0], [94.9, 670.0], [95.0, 671.0], [95.1, 679.0], [95.2, 681.0], [95.3, 683.0], [95.4, 686.0], [95.5, 688.0], [95.6, 690.0], [95.7, 693.0], [95.8, 697.0], [95.9, 699.0], [96.0, 702.0], [96.1, 705.0], [96.2, 706.0], [96.3, 708.0], [96.4, 712.0], [96.5, 714.0], [96.6, 717.0], [96.7, 719.0], [96.8, 721.0], [96.9, 724.0], [97.0, 727.0], [97.1, 731.0], [97.2, 733.0], [97.3, 736.0], [97.4, 738.0], [97.5, 741.0], [97.6, 744.0], [97.7, 746.0], [97.8, 749.0], [97.9, 752.0], [98.0, 760.0], [98.1, 762.0], [98.2, 765.0], [98.3, 768.0], [98.4, 771.0], [98.5, 776.0], [98.6, 780.0], [98.7, 783.0], [98.8, 787.0], [98.9, 795.0], [99.0, 814.0], [99.1, 824.0], [99.2, 831.0], [99.3, 835.0], [99.4, 839.0], [99.5, 843.0], [99.6, 884.0], [99.7, 924.0], [99.8, 1054.0], [99.9, 3221.0]], "isOverall": false, "label": "POST /api/v1/beta/translate", "isController": false}], "supportsControllersDiscrimination": true, "maxX": 100.0, "title": "Response Time Percentiles"}},
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
        data: {"result": {"minY": 1.0, "minX": 0.0, "maxY": 9901.0, "series": [{"data": [[0.0, 298.0], [600.0, 736.0], [2600.0, 1.0], [700.0, 651.0], [200.0, 5306.0], [3200.0, 1.0], [800.0, 146.0], [3700.0, 1.0], [900.0, 33.0], [1000.0, 14.0], [4300.0, 1.0], [1100.0, 13.0], [300.0, 9901.0], [4900.0, 1.0], [5500.0, 1.0], [1400.0, 1.0], [6100.0, 1.0], [6200.0, 16.0], [100.0, 402.0], [400.0, 2490.0], [2000.0, 1.0], [500.0, 1607.0]], "isOverall": false, "label": "POST /api/v1/beta/translate", "isController": false}], "supportsControllersDiscrimination": true, "granularity": 100, "maxX": 6200.0, "title": "Response Time Distribution"}},
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
        data: {"result": {"minY": 24.0, "minX": 0.0, "ticks": [[0, "Requests having \nresponse time <= 500ms"], [1, "Requests having \nresponse time > 500ms and <= 1,500ms"], [2, "Requests having \nresponse time > 1,500ms"], [3, "Requests in error"]], "maxY": 18402.0, "series": [{"data": [[0.0, 18402.0]], "color": "#9ACD32", "isOverall": false, "label": "Requests having \nresponse time <= 500ms", "isController": false}, {"data": [[1.0, 3196.0]], "color": "yellow", "isOverall": false, "label": "Requests having \nresponse time > 500ms and <= 1,500ms", "isController": false}, {"data": [[2.0, 24.0]], "color": "orange", "isOverall": false, "label": "Requests having \nresponse time > 1,500ms", "isController": false}, {"data": [], "color": "#FF6347", "isOverall": false, "label": "Requests in error", "isController": false}], "supportsControllersDiscrimination": false, "maxX": 2.0, "title": "Synthetic Response Times Distribution"}},
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
        data: {"result": {"minY": 12.436432637571153, "minX": 1.77361218E12, "maxY": 50.0, "series": [{"data": [[1.77361218E12, 12.436432637571153], [1.77361236E12, 49.82999115305218], [1.77361224E12, 47.34647723977968], [1.7736123E12, 50.0]], "isOverall": false, "label": "Threads", "isController": false}], "supportsControllersDiscrimination": false, "granularity": 60000, "maxX": 1.77361236E12, "title": "Active Threads Over Time"}},
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
        data: {"result": {"minY": 80.15584415584416, "minX": 1.0, "maxY": 5373.142857142858, "series": [{"data": [[32.0, 266.22058823529414], [33.0, 284.8840579710145], [34.0, 321.07142857142856], [35.0, 434.07317073170736], [36.0, 597.7209302325583], [37.0, 323.17391304347814], [38.0, 490.7931034482758], [39.0, 408.6493506493507], [40.0, 423.22950819672127], [41.0, 273.85185185185185], [42.0, 273.95959595959596], [43.0, 293.16666666666663], [44.0, 416.43333333333345], [45.0, 404.9861111111112], [46.0, 360.1971830985916], [47.0, 430.1176470588235], [48.0, 794.8510638297873], [49.0, 356.3456790123456], [3.0, 286.0], [50.0, 380.02682364985895], [4.0, 311.0], [7.0, 174.42857142857142], [8.0, 174.9142857142857], [9.0, 164.8214285714286], [10.0, 161.46153846153848], [11.0, 80.15584415584416], [12.0, 96.82666666666667], [13.0, 110.67692307692309], [14.0, 117.24637681159415], [15.0, 110.25333333333334], [16.0, 126.03389830508476], [1.0, 278.0], [17.0, 299.0], [20.0, 295.6666666666667], [22.0, 308.0], [25.0, 302.0], [26.0, 5373.142857142858], [27.0, 1434.6052631578948], [28.0, 223.01369863013696], [29.0, 235.26760563380284], [30.0, 277.49180327868845], [31.0, 231.35227272727275]], "isOverall": false, "label": "POST /api/v1/beta/translate", "isController": false}, {"data": [[48.184580519841, 376.66552585329754]], "isOverall": false, "label": "POST /api/v1/beta/translate-Aggregated", "isController": false}], "supportsControllersDiscrimination": true, "maxX": 50.0, "title": "Time VS Threads"}},
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
        data : {"result": {"minY": 3539.6833333333334, "minX": 1.77361218E12, "maxY": 91946.0, "series": [{"data": [[1.77361218E12, 3539.6833333333334], [1.77361236E12, 45552.433333333334], [1.77361224E12, 46331.566666666666], [1.7736123E12, 49804.083333333336]], "isOverall": false, "label": "Bytes received per second", "isController": false}, {"data": [[1.77361218E12, 6534.8], [1.77361236E12, 84096.8], [1.77361224E12, 85535.2], [1.7736123E12, 91946.0]], "isOverall": false, "label": "Bytes sent per second", "isController": false}], "supportsControllersDiscrimination": false, "granularity": 60000, "maxX": 1.77361236E12, "title": "Bytes Throughput Over Time"}},
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
        data: {"result": {"minY": 116.04743833017083, "minX": 1.77361218E12, "maxY": 402.2891436277822, "series": [{"data": [[1.77361218E12, 116.04743833017083], [1.77361236E12, 361.4141846063113], [1.77361224E12, 384.02725427660084], [1.7736123E12, 402.2891436277822]], "isOverall": false, "label": "POST /api/v1/beta/translate", "isController": false}], "supportsControllersDiscrimination": true, "granularity": 60000, "maxX": 1.77361236E12, "title": "Response Time Over Time"}},
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
        data: {"result": {"minY": 115.87855787476289, "minX": 1.77361218E12, "maxY": 402.27390424814536, "series": [{"data": [[1.77361218E12, 115.87855787476289], [1.77361236E12, 361.40179887938535], [1.77361224E12, 383.9844882574659], [1.7736123E12, 402.27390424814536]], "isOverall": false, "label": "POST /api/v1/beta/translate", "isController": false}], "supportsControllersDiscrimination": true, "granularity": 60000, "maxX": 1.77361236E12, "title": "Latencies Over Time"}},
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
        data: {"result": {"minY": 0.01268062518431144, "minX": 1.77361218E12, "maxY": 1.5256166982922212, "series": [{"data": [[1.77361218E12, 1.5256166982922212], [1.77361236E12, 0.01268062518431144], [1.77361224E12, 0.020440707451435194], [1.7736123E12, 0.017666891436277886]], "isOverall": false, "label": "POST /api/v1/beta/translate", "isController": false}], "supportsControllersDiscrimination": true, "granularity": 60000, "maxX": 1.77361236E12, "title": "Connect Time Over Time"}},
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
        data: {"result": {"minY": 9.0, "minX": 1.77361218E12, "maxY": 6241.0, "series": [{"data": [[1.77361218E12, 261.0], [1.77361236E12, 1180.0], [1.77361224E12, 6241.0], [1.7736123E12, 938.0]], "isOverall": false, "label": "Max", "isController": false}, {"data": [[1.77361218E12, 166.0], [1.77361236E12, 523.0], [1.77361224E12, 583.0], [1.7736123E12, 573.0]], "isOverall": false, "label": "90th percentile", "isController": false}, {"data": [[1.77361218E12, 223.72000000000003], [1.77361236E12, 782.3400000000001], [1.77361224E12, 840.0], [1.7736123E12, 771.0]], "isOverall": false, "label": "99th percentile", "isController": false}, {"data": [[1.77361218E12, 182.59999999999997], [1.77361236E12, 628.0], [1.77361224E12, 719.0], [1.7736123E12, 667.1999999999998]], "isOverall": false, "label": "95th percentile", "isController": false}, {"data": [[1.77361218E12, 68.0], [1.77361236E12, 222.0], [1.77361224E12, 9.0], [1.7736123E12, 236.0]], "isOverall": false, "label": "Min", "isController": false}, {"data": [[1.77361218E12, 109.0], [1.77361236E12, 322.0], [1.77361224E12, 319.0], [1.7736123E12, 362.0]], "isOverall": false, "label": "Median", "isController": false}], "supportsControllersDiscrimination": false, "granularity": 60000, "maxX": 1.77361236E12, "title": "Response Time Percentiles Over Time (successful requests only)"}},
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
    data: {"result": {"minY": 94.0, "minX": 14.0, "maxY": 796.0, "series": [{"data": [[14.0, 178.5], [26.0, 301.5], [29.0, 118.0], [37.0, 796.0], [43.0, 750.0], [49.0, 160.0], [50.0, 510.0], [65.0, 405.0], [66.0, 530.0], [67.0, 529.0], [70.0, 142.5], [68.0, 763.0], [71.0, 576.0], [69.0, 563.0], [74.0, 575.0], [73.0, 532.0], [76.0, 623.5], [78.0, 523.0], [77.0, 491.0], [81.0, 213.0], [80.0, 507.0], [86.0, 410.0], [85.0, 731.0], [87.0, 422.0], [90.0, 736.5], [92.0, 476.0], [95.0, 558.0], [94.0, 516.0], [99.0, 596.0], [102.0, 326.0], [100.0, 468.0], [105.0, 335.0], [104.0, 413.0], [107.0, 252.0], [106.0, 362.5], [110.0, 388.0], [109.0, 364.0], [108.0, 429.0], [115.0, 234.0], [112.0, 358.5], [113.0, 514.0], [114.0, 396.0], [117.0, 400.0], [116.0, 385.0], [119.0, 385.0], [118.0, 379.5], [123.0, 113.0], [121.0, 373.0], [122.0, 386.5], [120.0, 423.0], [127.0, 188.5], [126.0, 267.5], [124.0, 402.0], [125.0, 404.0], [132.0, 315.0], [129.0, 380.0], [130.0, 393.0], [133.0, 370.0], [128.0, 290.5], [131.0, 379.0], [140.0, 355.0], [137.0, 353.0], [141.0, 349.0], [138.0, 350.0], [136.0, 355.0], [142.0, 366.0], [151.0, 304.0], [149.0, 336.0], [150.0, 319.0], [146.0, 326.0], [147.0, 333.0], [145.0, 343.0], [144.0, 332.0], [156.0, 304.5], [155.0, 317.0], [154.0, 322.0], [158.0, 311.0], [157.0, 328.0], [152.0, 315.0], [161.0, 304.0], [162.0, 312.0], [160.0, 328.0], [163.0, 299.0], [174.0, 292.0], [171.0, 293.0], [169.0, 308.0], [175.0, 271.0], [172.0, 293.5], [170.0, 293.0], [179.0, 94.0], [191.0, 283.0], [184.0, 281.0], [187.0, 276.0], [193.0, 266.0], [200.0, 282.5]], "isOverall": false, "label": "Successes", "isController": false}], "supportsControllersDiscrimination": false, "granularity": 1000, "maxX": 200.0, "title": "Response Time Vs Request"}},
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
    data: {"result": {"minY": 94.0, "minX": 14.0, "maxY": 796.0, "series": [{"data": [[14.0, 173.5], [26.0, 301.5], [29.0, 118.0], [37.0, 796.0], [43.0, 750.0], [49.0, 160.0], [50.0, 510.0], [65.0, 405.0], [66.0, 530.0], [67.0, 529.0], [70.0, 142.5], [68.0, 763.0], [71.0, 576.0], [69.0, 563.0], [74.0, 575.0], [73.0, 532.0], [76.0, 623.0], [78.0, 523.0], [77.0, 491.0], [81.0, 213.0], [80.0, 507.0], [86.0, 410.0], [85.0, 731.0], [87.0, 422.0], [90.0, 736.5], [92.0, 476.0], [95.0, 558.0], [94.0, 516.0], [99.0, 596.0], [102.0, 326.0], [100.0, 468.0], [105.0, 335.0], [104.0, 413.0], [107.0, 252.0], [106.0, 362.5], [110.0, 388.0], [109.0, 364.0], [108.0, 429.0], [115.0, 234.0], [112.0, 358.0], [113.0, 514.0], [114.0, 396.0], [117.0, 400.0], [116.0, 385.0], [119.0, 385.0], [118.0, 379.5], [123.0, 113.0], [121.0, 373.0], [122.0, 386.5], [120.0, 423.0], [127.0, 188.5], [126.0, 267.5], [124.0, 402.0], [125.0, 404.0], [132.0, 315.0], [129.0, 380.0], [130.0, 393.0], [133.0, 370.0], [128.0, 290.5], [131.0, 379.0], [140.0, 355.0], [137.0, 353.0], [141.0, 349.0], [138.0, 350.0], [136.0, 355.0], [142.0, 366.0], [151.0, 304.0], [149.0, 336.0], [150.0, 319.0], [146.0, 326.0], [147.0, 333.0], [145.0, 343.0], [144.0, 332.0], [156.0, 304.5], [155.0, 317.0], [154.0, 322.0], [158.0, 311.0], [157.0, 328.0], [152.0, 315.0], [161.0, 304.0], [162.0, 312.0], [160.0, 328.0], [163.0, 299.0], [174.0, 292.0], [171.0, 293.0], [169.0, 308.0], [175.0, 271.0], [172.0, 293.5], [170.0, 293.0], [179.0, 94.0], [191.0, 282.0], [184.0, 281.0], [187.0, 276.0], [193.0, 266.0], [200.0, 282.0]], "isOverall": false, "label": "Successes", "isController": false}], "supportsControllersDiscrimination": false, "granularity": 1000, "maxX": 200.0, "title": "Latencies Vs Request"}},
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
        data: {"result": {"minY": 9.1, "minX": 1.77361218E12, "maxY": 123.58333333333333, "series": [{"data": [[1.77361218E12, 9.1], [1.77361236E12, 112.2], [1.77361224E12, 115.48333333333333], [1.7736123E12, 123.58333333333333]], "isOverall": false, "label": "hitsPerSecond", "isController": false}], "supportsControllersDiscrimination": false, "granularity": 60000, "maxX": 1.77361236E12, "title": "Hits Per Second"}},
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
        data: {"result": {"minY": 8.783333333333333, "minX": 1.77361218E12, "maxY": 123.58333333333333, "series": [{"data": [[1.77361218E12, 8.783333333333333], [1.77361236E12, 113.03333333333333], [1.77361224E12, 114.96666666666667], [1.7736123E12, 123.58333333333333]], "isOverall": false, "label": "200", "isController": false}], "supportsControllersDiscrimination": false, "granularity": 60000, "maxX": 1.77361236E12, "title": "Codes Per Second"}},
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
        data: {"result": {"minY": 8.783333333333333, "minX": 1.77361218E12, "maxY": 123.58333333333333, "series": [{"data": [[1.77361218E12, 8.783333333333333], [1.77361236E12, 113.03333333333333], [1.77361224E12, 114.96666666666667], [1.7736123E12, 123.58333333333333]], "isOverall": false, "label": "POST /api/v1/beta/translate-success", "isController": false}], "supportsControllersDiscrimination": true, "granularity": 60000, "maxX": 1.77361236E12, "title": "Transactions Per Second"}},
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
        data: {"result": {"minY": 8.783333333333333, "minX": 1.77361218E12, "maxY": 123.58333333333333, "series": [{"data": [[1.77361218E12, 8.783333333333333], [1.77361236E12, 113.03333333333333], [1.77361224E12, 114.96666666666667], [1.7736123E12, 123.58333333333333]], "isOverall": false, "label": "Transaction-success", "isController": false}, {"data": [], "isOverall": false, "label": "Transaction-failure", "isController": false}], "supportsControllersDiscrimination": true, "granularity": 60000, "maxX": 1.77361236E12, "title": "Total Transactions Per Second"}},
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

