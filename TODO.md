## observations of what we need to add or address
-~~on the analytics tab, none of the panels show data~~ DONE
-~~on the analytics tab, add some temporal options, such as "Last week", "Last 30 days", "Last 60 day", "Last 90 days"~~ DONE
-~~on the shot data tab, add more columns. Is it possible to add all of them and still maintain some "visibility" to all of it? I don't want to have to scroll left to right or squint to read, but we need more data there. Swing Size is definitely required.~~ DONE 
-~~change the selector for club from a dropdown to something clickable. I want to see all of the club types at the same time and click each to toggle it on or off. When clicked, I want it immediately reflected in what's shown.~~ DONE
-~~on the shot data page, including and excluding shots only works from the action column's buttons. The two individual "Exclude Selected" and "Include Selected" buttons above the table do not work.~~ DONE
-~~on the pocket card orient both matrices as portrait (not landscape)~~ DONE
-~~importing files doesn't work~~ DONE
-~~the shots tab is very slow when I try to add or remove clusbs.~~ DONE
-~~carry distance distribution on the analytics page doesn't work~~ DONE
-~~on the analytics page I want it to be easier to add or remove clubs~~ DONE
-~~when printed, the club matrix should measure about 2.5" across and 4" down~~ DONE
-~~when printed, the wedge matrix should be about 2.5" across and 3" down~~ DONE
-~~when printing the two matrices, ensure they print on the same single sheet of paper (to reduce paper waste). Keep them separate on the page so the user can 
cut them to size (for fitting in the pocket).~~ DONE
-~~when importing wedge data, there is a lot of scrolling of the page if you have a lot of shots. I should be able to mark a set of shots, any size I want, with their
swing size and then click import and the are processed and then removed from the screen. Then I can proceed with the next group of shots, set their sizes, and import
them.  This will minimize the scrolling needed.~~ DONE
-~~when wedge data is imported, give the user the option to select from the top a group of shots, such as "first 5", and then they can set the swing size. This will
minimize the need to click individual rows. -Let the user set the size of the selection group (don't fix it ag 5).~~ DONE
-~~do whatever scaling is necessary to make both matrices 37% wider when printed to paper~~ DONE
-~~Double the current font size on both printed matrices~~ DONE
-~~on the analytics page the charts render data for the "All" selection and for any single club selection, but never when more than one club is selected.~~ DONE
-~~for the club selector tool, change the selection behavior as follows: "All" selects every club. "None" de-selects every club. For everything else a selection is a single
club request, unless the user holds down the control key, then the club selection adds to what is already selected.~~ DONE
-~~the shot data page still performs poorly, likely due to the amount of data. Investigate what can be done to improve it. consider using the same club/date/session
selector controls from the analytics page on the shots page.~~ DONE
-~~the analytics page is missing percentile selection options~~ DONE
-~~at the bottom of every page with a percentile selection option, include some text that explains percentiles. Give some good, relatable, information so the user
can cearly understand the concept~~ DONE
-~~on the shots page, "hidden shots" should also be hidden from view. User should be able to toggle to see the hidden shots again, but default is to hide them~~ DONE
-~~on the analytics page, the dispersion pattern should always start from 0 on the carry axis. The point is to see the pattern from the POV of the origin point.~~ DONE
-~~based on analytics data, some shots should be suggested for exclusion. add some type of a "suggested excluded shots" to the shots page that the user can review
and agree (or disagree) to the exclusion~~ DONE
-~~on the analytics page does the refresh button serve a purpose?~~ DONE
-~~for the percentile commentary, do a better job explaining the differences between percentile numbers and why you see the numbers go up when the percentile numbers
go up.~~ DONE
-~~on the two matrix cards make the height of the table dynamically determined based on the number of rows~~ DONE
-~~when printed, the two matrices are now slightly too wide. Reduce the printed width by 10%~~ DONE
-~~on the printed matrices the percentile used should be the percentile selected on the page when "Print Card" was chosen~~ DONE
-~~on the printed matrices cards, show the applicable percentile and the date printed at the bottom, below each matrix. Just show the date in mm/dd/yyyy format, with
nothing else. For the Percentile, just show the Percentile with the number, as in Pnn. Left-justify the percentile. Right-justify the date.~~ DONE
-~~on the club matrix, remove "My Distances" from the top.~~ DONE
-~~add pdf to gitignore and remove any committed pdf files~~ DONE
-~~for the chart comparing spin to carry distance, it would make more sense to compare it to the roll (total-carry)~~ DONE
-~~on the analytics page refresh the data if a different session is selected from the drop-down~~ DONE
-~~when printing the club matrices, remove the title above the club matrix.~~ DONE
-~~Rewrite the "Understanding Percentiles" sections with this key principle in mind: a golfer cannot choose which percentile they hit. They swing their best every time. The shot lands where it lands. Percentiles describe the natural variation in their past shots and help them make smarter pre-shot decisions, like club selection or deciding whether to go for a green. Do not imply the golfer can "dial up" a P75 or P90 shot. Instead, frame percentiles as a planning tool based on historical tendencies. Keep the tone brief and practical, like advice from a caddie. No em dashes. Short sentences only.~~ DONE
-~~in a previous to-do a "suggested excluded shots" feature was requested but it has not materialized yet. This is required.~~ DONE
-~~keep requesting to remove the "Club Distances" text from the club matrix. See image at "C:\Users\ersabine\OneDrive - Microsoft\Pictures\screenshots\Screenshot 2026-03-19 152602.png"~~ DONE
-~~the dynamic loft trend doesn't seem that helpful, remove it~~ DONE
-~~the sort ordering for clubs isn't correct. Clubs should be presented in the order Woods, Hybrids, Irons, and last Wedges. Sort numerically for the first 3 groups.  For the wedges, the sort order is as follows: PW, AW, SW, LW.~~ DONE
-~~For the carry distance distribution, the gapping between each club is an important metric. It should be the focus of the chart.~~ DONE
-~~in the analytics chart, add a Launch-Spin Stability Box Plot for each club. Use Spin Rate (rpm) and Launch Angle (degrees) as the primary variables. The visualization must include: (a) The Median (the center line) to identify my typical flight. (b) The Interquartile Range (IQR) (the box) to measure the stability of my core shots. (c) Whiskers and Outliers to highlight 'fliers' or 'balloon' shots. Once rendered, analyze any high-variance clusters by correlating them with Attack Angle and Ball Speed to determine if the instability is caused by poor strike quality (low smash) or mechanical inconsistencies in the swing arc.~~ DONE
-~~in the analytics chart, add a radar (spider) chart showing 5–6 key metrics (e.g., Carry, Dispersion, Smash, Spin, Launch). Plot the percentile vs. a "PGA Tour Average" to see where my biggest gaps lie~~ DONE
-~~"Launch & Spin Stability" doesn't render any data~~ DONE
-~~"My Shots vs PGA Tour Average" doesn't render any data~~ DONE
-~~multiple charts on the Analytics tab do not seem to be affected by the percentile seection~~ DONE
-~~when generating the matrix printable cards, the percentile showing at the time of selection is not utilized. The matrices remain at P75.~~ DONE
-~~reduce the width of the printable matrices by 5%~~ DONE
-~~we need the ability to load data for testing but easily mark it for separation from the data the user has loaded. Add that facility to the session table and then give the ability to show/hide test data from the same screen~~ DONE
-~~Remove the 4/4 swing size from the wedge matrix. Rename 3/4 to 3/3, 2/4 to 2/3, and 1/4 to 1/3.~~ DONE
-~~In the wedge matrix, add the PW column to the left of AW. Make each column narrower to obtain the room.~~ DONE
-~~In the dispersion pattern chart, add a dotted line at the 0 of the offline (x) axis. If it doesn't add to the clutter, you can label it "Target"~~ DONE
-~~In the dispersion pattern chart, add a P90 "dispersion area" around the P90 shots at a per-club basis. If the chart is too crowded to have this visible for every club, then only add it once the number of clubs has been reduced to some quantity where the P90s "circles" are not too cluttered. The dispersion area should probably be a dotted line and should be the same color as the club, unless we are showing just one club. Then you can make the color of it red.  The dispersion area should be a smoothed (as opposed to jagged) object and would be expected to take whatever shape the data drives it to be, but it should end where it starts, i.e., it should be some type of a loop but without being forced to be circular - unless the data warranted it being circular.~~ DONE
-~~The dispersion chart has a fundmental flaw. It treats the carry distance as a literal distance from a point directly below it, perpendicular to the x axis, where y=0. This is incorrect. All distances are measured from the target, where offline is 0 yards. The distance provided in the CSV file is the distance the ball travelled from the launch point. With no left or right spin the ball travels in a straight line, but with spin there is technically some curvature to the ball's flight path. For now, ignore the curvature and simply treat the carry distance as the hypotenuse of a triangle where both x and y need to be calculated.~~ DONE
-~~Launch & spin stability chart isn't using the launch angle properly. There seems to have been no effort to analyze high-variance clusters.~~ DONE
-~~What is being used for the PGA tour average numbers? That feature seems incomplete.~~ DONE
-~~The placement of the gapping numbers in the "Carry Distance & Gapping" is awkward and misleading. The gapping is between columns, not above them.~~ DONE
-~~For the dispersion chart, the "dispersion area" should always be the 90th percentile of the data rendered in the diagram, regardless of what percentile of shots are being shown.~~ DONE
-~~implement a version number that is also visibile at the bottom of every page of the ui~~ DONE
-~~there is no gap shown between the last two clubs in the carry distance & gapping chart~~ DONE
-~~when mousing over a shot of the dispersion pattern chart, include additional details like spin, descending loft, ball speed, face angle~~ DONE
-~~the launch and spin stability chart: widen and break down wedges into sub-swings~~ DONE
-~~the club comparison chart: rewrite as box and whisker plot~~ DONE
-~~my shots vs pga tour average: add per-club dropdown~~ DONE
-~~for the carry distance, can the chart have distances laid out like they were concentric circles. See this image "C:\Users\ersabine\OneDrive - Microsoft\Documents\Personal\wedgeMatrix\carry_distance_arch.png"~~ DONE
-~~for the 'club comparisons' and 'launch & spin stability', try the order as follows; 1W, 3W, 2H, 3H, 4H, 3i, 4i, 5i, 6i, 7i, 8i, 9i, PW-Full, AW-Full, SW-Full, LW-Full, AW-3/3, SW-3/3, LW-3/3, AW-2/3, SW-2/3, LW-2/3, AW-1/3, SW-1/3, LW-1/3, SW-10:2, LW-10:2, SW-10:3, LW-10:3, SW-9:3, LW-9:3, SW-8:4, LW-8:4. Note some clubs were mentioned that have not been seen in the data yet.~~ DONE
-~~the data imported for swing path is being misinterpreted. When preceded with L the swing path is out-to-in. When R, it is in-to-out. In the shot shape analysis the bulk of the data suggests the shots are mostly out-to-in, which is not correct for the user's profile of play.~~ DONE
-~~the version number should increment every time changes are made~~ DONE
-~~show a table at the bottom of the analytics page of the PGA tour average details. At present it looks like the numbers are broken.~~ DONE
-~~for the x axis of Dispersion Pattern, show the same number of yards to the left of 0 as are shown right.~~ DONE
-~~for the x axis label of Dispersion Pattern, place the words "Offline (Yards)" on a 2nd line of text. Everything should be center-justified and given the TODO above, the pipe should appear directly under the 0.~~ DONE
-~~when you mouse over a dot on Shot Shape Analysis, the popup should show the club~~ DONE
-~~the respective color of each club should be the same across each of these charts: Carry Distance & Gapping, Dispersion Pattern, Spin Rate vs Roll Distance, Shot Shape Analysis~~ DONE
-~~in the club comparison and launch & spin stability charts, remove AW-4/4, LW-4/4, and SW-4/4. The data for AW-full, SW-full, and LW-full, should come between PW and AW-3/3.  Remove "-full" from AW-full, SW-full, and LW-full.~~ DONE
-~~Under Shot Shape Analysis, move "Club Path (°)" to the second line. Center the text under the 0 of the X axis.~~ DONE
-~~Under Shot Shape Analysis, move "Face Angle (°)" to the first line, the remainder to the second line. Center-justify the text, but also line it up so the pipe (|) is directly to the left of the 0 of the Y axis.~~ DONE
-~~on both the wedge matrix and club matrix pages, when I hold the mouse over any of the data, a popup should show me how many data points are behind that number and the oldest date of data~~ DONE
-~~on both the wedge matrix and club matrix pages I want a field that I can type in the number of shots to limit each number's population to, for example if I enter 30, then for every individual calculation, only the most recent 30 shots for that club and swing type calculation should be used. The percentiles are still applicable, so if I had selected 30 for the count and P75, then show the 75th percentile of those 30 most recent shots for the club & swing type combo.~~ DONE
-~~on the printed wedge matrix card, add the total (as in carry/total) like we're doing with the clock shots~~ DONE
-~~on the printed wedge matrix card, add columns for 9 iron and 8 iron~~ DONE
-~~remove 8i and 9i from the printed wedge matrix~~ DONE
-~~the font size on the wedge matrix should match that of the iron matrix~~ DONE
-~~the printed wedge matrix needs to be a little wider. See the image at C:\Users\esabi\OneDrive\Pictures\Screenshots 1\wedgecards.png. You can see it needs to be wider to see all the printed text.~~ DONE
-we will be adding the ability to export a csv from the wedge matrix. When exporting, the clubs need to be exported with some translations. 1w should be Dr. All other *w can be exported as is.  All clubs ending in H should be exported as Hy, as in 2H becomes 2Hy. All other mappings we have now should be good as they are.  Add this new mapping to the club table.
-the csv export will be used to bring the data to shotpattern, an app on the iphone. The columns in the csv are these 5. Club, Type, Target, Total, and Side. Club is the club used. Type is one of 2 values, either Tee or Approach. Set to "Tee" when the club ends in W. Use Approach for everything else. I only want the "Full" swing data to be in the csv export. For "Target" use my "Max" less 10%. 