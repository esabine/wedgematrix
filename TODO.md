## observations of what we need to add or address
-on the analytics tab, none of the panels show data
-on the analytics tab, add some temporal options, such as "Last week", "Last 30 days", "Last 60 day", "Last 90 days"
-on the shot data tab, add more columns. Is it possible to add all of them and still maintain some "visibility" to all of it? I don't want to have to scroll left to right or squint to read, but we need more data there. Swing Size is definitely required. 
-change the selector for club from a dropdown to something clickable. I want to see all of the club types at the same time and click each to toggle it on or off. When clicked, I want it immediately reflected in what's shown.
-on the shot data page, including and excluding shots only works from the action column's buttons. The two individual "Exclude Selected" and "Include Selected" buttons above the table do not work.
-on the pocket card orient both matrices as portrait (not landscape)
-importing files doesn't work
-the shots tab is very slow when I try to add or remove clusbs.
-carry distance distribution on the analytics page doesn't work
-on the analytics page I want it to be easier to add or remove clubs
-when printed, the club matrix should measure about 2.5" across and 4" down
-when printed, the wedge matrix should be about 2.5" across and 3" down
-when printing the two matrices, ensure they print on the same single sheet of paper (to reduce paper waste). Keep them separate on the page so the user can 
cut them to size (for fitting in the pocket).
-when importing wedge data, there is a lot of scrolling of the page if you have a lot of shots. I should be able to mark a set of shots, any size I want, with their
swing size and then click import and the are processed and then removed from the screen. Then I can proceed with the next group of shots, set their sizes, and import
them.  This will minimize the scrolling needed.
-when wedge data is imported, give the user the option to select from the top a group of shots, such as "first 5", and then they can set the swing size. This will
minimize the need to click individual rows. -Let the user set the size of the selection group (don't fix it ag 5).
-do whatever scaling is necessary to make both matrices 37% wider when printed to paper
-Double the current font size on both printed matrices
-on the analytics page the charts render data for the "All" selection and for any single club selection, but never when more than one club is selected.
-for the club selector tool, change the selection behavior as follows: "All" selects every club. "None" de-selects every club. For everything else a selection is a single
club request, unless the user holds down the control key, then the club selection adds to what is already selected.
-the shot data page still performs poorly, likely due to the amount of data. Investigate what can be done to improve it. consider using the same club/date/session
selector controls from the analytics page on the shots page.
-the analytics page is missing percentile selection options
-at the bottom of every page with a percentile selection option, include some text that explains percentiles. Give some good, relatable, information so the user
can cearly understand the concept
-on the shots page, "hidden shots" should also be hidden from view. User should be able to toggle to see the hidden shots again, but default is to hide them
-on the analytics page, the dispersion pattern should always start from 0 on the carry axis. The point is to see the pattern from the POV of the origin point.
-based on analytics data, some shots should be suggested for exclusion. add some type of a "suggested excluded shots" to the shots page that the user can review
and agree (or disagree) to the exclusion
-on the analytics page, does the refresh button serve a purpose?
-for the percentile commentary, do a better job explaining the differences between percentile numbers and why you see the numbers go up when the percentile numbers
go up.
-on the two matrix cards make the height of the table dynamically determined based on the number of rows
-when printed, the two matrices are now slightly too wide. Reduce the printed width by 10%
-on the printed matrices the percentile used should be the percentile selected on the page when "Print Card" was chosen
-on the printed matrices cards, show the applicable percentile and the date printed at the bottom, below each matrix. Just show the date in mm/dd/yyyy format, with
nothing else. For the Percentile, just show the Percentile with the number, as in Pnn. Left-justify the percentile. Right-justify the date.
-on the club matrix, remove "My Distances" from the top.
-add pdf to gitignore and remove any committed pdf files
-for the chart comparing spin to carry distance, it would make more sense to compare it to the roll (total-carry)
-on the analytics page refresh the data if a different session is selected from the drop-down
-when printing the club matrices, remove the title above the club matrix.
-Rewrite the "Understanding Percentiles" sections with this key principle in mind: a golfer cannot choose which percentile they hit. They swing their best every time. The shot lands where it lands. Percentiles describe the natural variation in their past shots and help them make smarter pre-shot decisions, like club selection or deciding whether to go for a green. Do not imply the golfer can "dial up" a P75 or P90 shot. Instead, frame percentiles as a planning tool based on historical tendencies. Keep the tone brief and practical, like advice from a caddie. No em dashes. Short sentences only.
-in a previous to-do a "suggested excluded shots" feature was requested but it has not materialized yet. This is required.
-keep requesting to remove the "Club Distances" text from the club matrix. See image at "C:\Users\ersabine\OneDrive - Microsoft\Pictures\screenshots\Screenshot 2026-03-19 152602.png"
-the dynamic loft trend doesn't seem that helpful, remove it
-the sort ordering for clubs isn't correct. Clubs should be presented in the order Woods, Hybrids, Irons, and last Wedges. Sort numerically for the first 3 groups.  For the wedges, the sort order is as follows: PW, AW, SW, LW.
-For the carry distance distribution, the gapping between each club is an important metric. It should be the focus of the chart.
-in the analytics chart, add a Launch-Spin Stability Box Plot for each club. Use Spin Rate (rpm) and Launch Angle (degrees) as the primary variables. The visualization must include: (a) The Median (the center line) to identify my typical flight. (b) The Interquartile Range (IQR) (the box) to measure the stability of my core shots. (c) Whiskers and Outliers to highlight 'fliers' or 'balloon' shots. Once rendered, analyze any high-variance clusters by correlating them with Attack Angle and Ball Speed to determine if the instability is caused by poor strike quality (low smash) or mechanical inconsistencies in the swing arc.
-in the analytics chart, add a radar (spider) chart showing 5–6 key metrics (e.g., Carry, Dispersion, Smash, Spin, Launch). Plot the percentile vs. a "PGA Tour Average" to see where my biggest gaps lie
-"Launch & Spin Stability" doesn't render any data
-"My Shots vs PGA Tour Average" doesn't render any data
-multiple charts on the Analytics tab do not seem to be affected by the percentile seection
-when generating the matrix printable cards, the percentile showing at the time of selection is not utilized. The matrices remain at P75.
-reduce the width of the printable matrices by 5%
-we need the ability to load data for testing but easily mark it for separation from the data the user has loaded. Add that facility to the session table and then give the ability to show/hide test data from the same screen
-Remove the 4/4 swing size from the wedge matrix. Rename 3/4 to 3/3, 2/4 to 2/3, and 1/4 to 1/3.
-In the wedge matrix, add the PW column to the left of AW. Make each column narrower to obtain the room.
-In the dispersion pattern chart, add a dotted line at the 0 of the offline (x) axis. If it doesn't add to the clutter, you can label it "Target"
-In the dispersion pattern chart, add a P90 "dispersion area" around the P90 shots at a per-club basis. If the chart is too crowded to have this visible for every club, then only add it once the number of clubs has been reduced to some quantity where the P90s "circles" are not too cluttered. The dispersion area should probably be a dotted line and should be the same color as the club, unless we are showing just one club. Then you can make the color of it red.  The dispersion area should be a smoothed (as opposed to jagged) object and would be expected to take whatever shape the data drives it to be, but it should end where it starts, i.e., it should be some type of a loop but without being forced to be circular - unless the data warranted it being circular.
-The dispersion chart has a fundmental flaw. It treats the carry distance as a literal distance from a point directly below it, perpendicular to the x axis, where y=0. This is incorrect. All distances are measured from the target, where offline is 0 yards. The distance provided in the CSV file is the distance the ball travelled from the launch point. With no left or right spin the ball travels in a straight line, but with spin there is technically some curvature to the ball's flight path. For now, ignore the curvature and simply treat the carry distance as the hypotenuse of a triangle where both x and y need to be calculated.
-Launch & spin stability chart isn't using the launch angle properly. There seems to have been no effort to analyze high-variance clusters.
-What is being used for the PGA tour average numbers? That feature seems incomplete.
-The placement of the gapping numbers in the "Carry Distance & Gapping" is awkward and misleading. The gapping is between columns, not above them.
-For the dispersion chart, the "dispersion area" should always be the 90th percentile of the data rendered in the diagram, regardless of what percentile of shots are being shown.
-~~implement a version number that is also visibile at the bottom of every page of the ui~~ DONE
-~~there is no gap shown between the last two clubs in the carry distance & gapping chart~~ DONE
-~~when mousing over a shot of the dispersion pattern chart, include additional details like spin, descending loft, ball speed, face angle~~ DONE
-~~the launch and spin stability chart: widen and break down wedges into sub-swings~~ DONE
-~~the club comparison chart: rewrite as box and whisker plot~~ DONE
-~~my shots vs pga tour average: add per-club dropdown~~ DONE
