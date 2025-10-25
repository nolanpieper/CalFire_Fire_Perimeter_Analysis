#This script takes in the CalFire historic fire perimeter feature class dataset and,
#subselects fires based on years of interest, merges them into a new feature class and,
#performs a hotspot statistical analysis on the new features.
#additionally creates a statistics summary table for fire data

import arcpy

import traceback

arcpy.env.overwriteOutput = True
arcpy.env.workspace = r"C:\PSU\GEOG485\FinalProjectData\fire24_1.gdb"

#input variables
firePerimeterFC = "firep24_1" #input feature class (FC)
summaryTable = "fire_summary" #output summary table name
yearsOfInterest = [2019, 2020] #fire years of interest
yearField = 'YEAR_' #year field from input FC
acresField = "GIS_ACRES" #acres field from input FC
startdateField = "ALARM_DATE" #start date field from input FC
enddateField = "CONT_DATE" # end date field from input FC


#functions for analysis:

#function to calculate the total acres and days for the input feature class
def calculateTotals (inputFC, acres_field, start_field, end_field):
    #initialize counters for totals
    totalAcres = 0
    totalDays = 0

    #use a cursor to select the necessary records from the input feature class
    with arcpy.da.SearchCursor(inputFC, [acres_field, start_field, end_field]) as cursorS:
        for field in cursorS:
            if field[0]:
                #add acres to the total acres counter
                totalAcres += field[0]

            if field[1] and field[2]:
                #add the days to the total days counter
                totalDays += (field[2] - field[1]).days

    return totalAcres, totalDays

#function that creates a feature class for each fire year of interest
def createFireYearFC (inputFC, year, year_field):
    whereClause = f"{year_field} = {year}"

    #select the fires from the years of interest
    fireYearLayer = arcpy.management.SelectLayerByAttribute(inputFC, "NEW_SELECTION", whereClause)

    #create an output storage
    outputFireYears = f"fires_{year}"

    #copy features to new output
    arcpy.management.CopyFeatures(fireYearLayer, outputFireYears)

    #delete feature layer
    arcpy.management.Delete(fireYearLayer)

    return(outputFireYears)

#function that creates and populates summary table for a selected year of fires
def createSummaryTable (table, year, year_acres, year_days, total_acres, total_days):

    #calculate values for summary statistics table
    percentOfTotalAcres = (year_acres / total_acres) * 100 if total_acres else 0
    percentOfTotalDays = (year_days / total_days) * 100 if total_days else 0

    #insert values into summary statistics table
    with (arcpy.da.InsertCursor(table, ["Year", "AcresBurnt", "BurnDays",
                                       "PercentOfTotalAcres", "PercentOfTotalDays"])
          as cursorI):
        cursorI.insertRow([year, year_acres, year_days, percentOfTotalAcres, percentOfTotalDays])

    print(f"created summary table for {year}")

#function to merge the features into one and clean up intermediate features
def mergeAndClean (fireYearSelectList, mergedOutputs):

    #merge the created fire year feature classes from a list of fire year outputs
    arcpy.management.Merge(fireYearSelectList, mergedOutputs)

    #delete intermediate features
    for fireYear in fireYearSelectList:
        arcpy.management.Delete(fireYear)

    print("merged feature classes and deleted intermediate features.")


#main script
try:
    #create summary table
    arcpy.management.CreateTable(arcpy.env.workspace, summaryTable)
    arcpy.management.AddFields(summaryTable, [
        ["Year", "LONG"],
        ["AcresBurnt", "DOUBLE"],
        ["BurnDays", "DOUBLE"],
        ["PercentOfTotalAcres", "DOUBLE"],
        ["PercentOfTotalDays", "DOUBLE"]
        ])

    print('Created summary table and added fields fields')


    #gather totals for acres and days for the whole fire perimeter data set
    totalAcres, totalDays = calculateTotals(firePerimeterFC, acresField, startdateField, enddateField)

    print(f"Calculated total acres: {totalAcres}")
    print(f"Calculated total days: {totalDays}")

    #create a list to store the selected fire year feature classes to merge
    fcOutputMergeList = []

    #loop through each select year of fires
    for year in yearsOfInterest:
        outputFC = createFireYearFC(firePerimeterFC, year, yearField)
        #append each selected fire year to the empty list
        fcOutputMergeList.append(outputFC)

        #calculate the total acres and days for each selected fire year
        acresInYear, daysInYear = calculateTotals(outputFC, acresField, startdateField, enddateField)

        print(f"{year} had {acresInYear} acres burnt and {daysInYear} burn days.")


        #populate the yearly summary into the summary table
        createSummaryTable(summaryTable, year, acresInYear, daysInYear, totalAcres, totalDays)


    #merge the outputs into one feature class
    mergedOutputs = "fires_2019_2020"
    mergeAndClean(fcOutputMergeList, mergedOutputs)

    # Run Hot Spot Analysis on merged outputs
    hotspotOutput = "hotspots_2019_2020"
    arcpy.stats.HotSpots(
        Input_Feature_Class=mergedOutputs,
        Input_Field=acresField,
        Output_Feature_Class=hotspotOutput,
        Conceptualization_of_Spatial_Relationships="CONTIGUITY_EDGES_CORNERS",
        Distance_Method="EUCLIDEAN_DISTANCE"
    )
    print("Hot Spot Analysis complete")

    print("Script completed successfully!")

except Exception as e:
    print("ERROR: Exception caught:")
    traceback.print_exc()
    print(f"Exception message: {e}")
    # Also log to ArcGIS geoprocessing messages
    try:
        arcpy.AddError(str(e))
        arcpy.AddMessage(traceback.format_exc())
    except:
        pass
