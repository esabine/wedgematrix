I am a golf fanatic and I love data and analytics. I have a need for some type of an application that can ingest data extracted from my golf launch monitor and use said data to build an analytics tool. I don't have any preference on the application. But I can tell you some specifics that I hope we can use to create a product requirements document.

-there should be a user interface that is capable of showing me data grouped in a number of ways.
-percentiles mean more than basic averages, mins, and maxes
-there are two matrices that are of utmost importance to me. So much so, that I need to be able to print these out into a pocket sized card that I carry with me when I play golf. The two are the club matrix and the wedge matrix.
-the club matrix has all clubs from driver down to lob wedge. The columns will be Club, Carry, Total, and Max. Carry and Total are each going to be columns in the CSV data. Max is the one time it's ok to use a maximum value. That value will be based on the club groupings.
-the wedge matrix will contain 4 columns as well: "swing size", AW (which is another name for the Gap Wedge - or GW), SW (for sand wedge), and LW (for lob wedge). I can divide my swing size into 8 levels, which are 4/4, 3/4, 2/4, 1/4, 10:2, 10:3, 9:3, and 8:4. For the 4 clock-hand sizes, the numbers in the matrix cell will be Carry/Max.  You will see an example of this in an image I share. In the image, disregard that 3/4 and 1/2 have two rows each. That was a mistake in the preparation.
-when I bring new data, it will always be in a csv file. The files will have unique names. I can provide you two samples of the files when we get started.
-when I bring new data to the app, I should be asked if it is wedge data or club data. When it is club data the swing size is always "full".  When it is wedge data, I should have the ability to label every row as one of those 8 sizes.
-I want the ability to see my club data from multiple csv files and also the ability to see just one at a time.
-There will be errant shot data in the files that I would like to ignore. Ideally by using percentiles, the errant data would be ignored, but the ability to completely any given row of data should be available.
-In the CSV data the clubs will appear like "5 Iron" but in the matrix you will see simply 5i. There are 4 wedges; Pitching, Gap, Sand, and Lob. Gap and Anywhere are the same wedge.
-All golf clubs have a fixed angle. In the CSV data you will see the Dynamic Loft column. Good golf shots have a dynamic loft lower than the club's fixed angle. The application should help me know when my attack angle is good and when it is bad.
-There are other valuable details in the data like spin rate, offline, landing angle, etc. You should investigate how to interpret those and help build better analytics.

Using this information I've provided and any interview questions you want to ask, build a requirements plan document that I can then provide to my squad to build.