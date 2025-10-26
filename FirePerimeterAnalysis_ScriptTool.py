#script tool for fire perimeter analysis that takes in the CalFire historic fire perimeter dataset and,
#selects a subset of fires from a year range and creates a new feature class, summary table of statistics and,
#a statistical hot spot analysis

import arcpy

arcpy.env.overwriteOutput = True

#script tool parameters
firePerimeterFC = arcpy.GetParameterAsText(0)  #fire perimeter input feature class
startYear = int(arcpy.GetParameterAsText(1))   #start year
endYear = int(arcpy.GetParameterAsText(2))     #end year
arcpy.env.workspace = arcpy.GetParameterAsText(3)  #workspace

#output variable names
summaryTable = f"fire_summary_{startYear}_{endYear}"

#necessary field names from input FC
yearField = 'YEAR_'          #year field in the fire FC
acresField = "GIS_ACRES"     #acres burned field
startdateField = "ALARM_DATE"  #fire start date field
enddateField = "CONT_DATE"     #fire end date field

#list of years
yearsOfInterest = list(range(startYear, endYear + 1))


#script functions:

#function calculates the total acres burnt and burn days from the entire input FC
def calculateTotals(inputFC, acres_field, start_field, end_field):
    totalAcres = 0
    totalDays = 0
    with arcpy.da.SearchCursor(inputFC, [acres_field, start_field, end_field]) as cursorS:
        for field in cursorS:
            if field[0]:
                totalAcres += field[0]
            if field[1] and field[2]:
                totalDays += (field[2] - field[1]).days
    return totalAcres, totalDays

#function creates feature classes for each selected fire year
def createFireYearFC(inputFC, year, year_field):
    whereClause = f"{year_field} = {year}"
    fireYearLayer = arcpy.management.MakeFeatureLayer(inputFC, f"fireLayer_{year}", whereClause)
    outputFireYears = f"fires_{year}"
    arcpy.management.CopyFeatures(fireYearLayer, outputFireYears)
    arcpy.management.Delete(fireYearLayer)
    return outputFireYears

#function creates a summary table for the output
def createSummaryTable(table, year, year_acres, year_days, total_acres, total_days):
    percentOfTotalAcres = (year_acres / total_acres) * 100 if total_acres else 0
    percentOfTotalDays = (year_days / total_days) * 100 if total_days else 0

    with arcpy.da.InsertCursor(table, ["Year", "AcresBurnt", "BurnDays",
                                       "PercentOfTotalAcres", "PercentOfTotalDays"]) as cursorI:
        cursorI.insertRow([year, year_acres, year_days, percentOfTotalAcres, percentOfTotalDays])
    arcpy.AddMessage(f"Created summary table for {year}")

#function merges the selected fire year feature classes and deletes the intermediate layers
def mergeAndClean(fireYearSelectList, mergedOutputs):
    arcpy.management.Merge(fireYearSelectList, mergedOutputs)
    for fireYear in fireYearSelectList:
        arcpy.management.Delete(fireYear)
    arcpy.AddMessage("Merged feature classes and deleted intermediate features.")


#main script execution
try:
    #create the summary table
    arcpy.management.CreateTable(arcpy.env.workspace, summaryTable)
    arcpy.management.AddFields(summaryTable, [
        ["Year", "LONG"],
        ["AcresBurnt", "DOUBLE"],
        ["BurnDays", "DOUBLE"],
        ["PercentOfTotalAcres", "DOUBLE"],
        ["PercentOfTotalDays", "DOUBLE"]
    ])
    arcpy.AddMessage('Created summary table and added fields.')

    #calculate the totals for the entire dataset
    totalAcres, totalDays = calculateTotals(firePerimeterFC, acresField, startdateField, enddateField)
    arcpy.AddMessage(f"Total acres: {totalAcres}, Total burn days: {totalDays}")

    #create a list to store the intermediate feature classes to be merged
    fcOutputMergeList = []

    #loop through the selected fire years, calculate their totals and append them to the list
    for year in yearsOfInterest:
        outputFC = createFireYearFC(firePerimeterFC, year, yearField)
        fcOutputMergeList.append(outputFC)
        acresInYear, daysInYear = calculateTotals(outputFC, acresField, startdateField, enddateField)
        arcpy.AddMessage(f"{year} had {acresInYear} acres burned and {daysInYear} burn days.")
        createSummaryTable(summaryTable, year, acresInYear, daysInYear, totalAcres, totalDays)

    #merge the selected years into one feature class
    mergedOutputs = f"fires_{startYear}_{endYear}"
    mergeAndClean(fcOutputMergeList, mergedOutputs)

    #run the hot spot analysis
    hotspotOutput = f"hotspots_{startYear}_{endYear}"
    arcpy.stats.HotSpots(
        Input_Feature_Class=mergedOutputs,
        Input_Field=acresField,
        Output_Feature_Class=hotspotOutput,
        Conceptualization_of_Spatial_Relationships="CONTIGUITY_EDGES_CORNERS",
        Distance_Method="EUCLIDEAN_DISTANCE"
    )
    arcpy.AddMessage("Hot Spot Analysis complete.")
    arcpy.AddMessage("Script completed successfully!")

except:
    arcpy.AddError(f"Error occurred")
    arcpy.AddError(arcpy.GetMessages())

