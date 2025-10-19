# Script builds on basescript adapting it to accommodate for multiple years

import arcpy

arcpy.env.overwriteOutput = True
arcpy.env.workspace = r"C:\PSU\GEOG485\FinalProjectData\fire24_1.gdb"

# Base feature class variable
firePerimeterFC = "firep24_1"
summaryTable = "fire_summary"

# Records of interest variables
yearsOfInterest = [2025, 2024, 2023, 2022, 2021, 2020]

# Fields of interest variables
yearField = 'YEAR_'
acresField = "GIS_ACRES"
startdateField = "ALARM_DATE"
enddateField = "CONT_DATE"

# Counter variables for ALL years combined
totalAcresBurntCounter = 0
totalBurnDaysCounter = 0

# New field variables for the fires in each year
firesPercentageOfAcreageBurnt = 'PercentOfTotalAcres'
firesPercentageofDaysBurnt = 'PercentOfTotalDays'
dataType = 'DOUBLE'

# Delete table if it already exists
if arcpy.Exists(summaryTable):
    arcpy.management.Delete(summaryTable)

# Create an empty table
arcpy.management.CreateTable(arcpy.env.workspace, summaryTable)

# Add fields
arcpy.management.AddFields(summaryTable, [
    ["Year", "LONG"],
    ["TotalAcres", "DOUBLE"],
    ["TotalDays", "DOUBLE"],
    ["PofAllAcres", "DOUBLE"],
    ["PofAllDays", "DOUBLE"]
])
print('Created summary table and fields')

# Get a total count of burnt acres and days on fire from master dataset
with arcpy.da.SearchCursor(firePerimeterFC, [acresField, startdateField, enddateField]) as totalCountsCursor:
    for totalCounts in totalCountsCursor:
        if totalCounts[0]:
            totalAcresBurntCounter += totalCounts[0]
        if totalCounts[1] and totalCounts[2]:
            totalBurnDaysCounter += (totalCounts[2] - totalCounts[1]).days

print(f"Total acres burnt (all years): {totalAcresBurntCounter:,.0f}")
print(f"Total burn days (all years): {totalBurnDaysCounter:,.0f}")

try:
    for year in yearsOfInterest:
        # RESET COUNTERS FOR EACH YEAR - THIS IS THE FIX!
        totalAcresBurntInYearCounter = 0
        totalBurnDaysInYearCounter = 0

        yearQuery = f"{yearField} = {year}"

        # SelectLayerByAttribute returns a layer object
        yearsLayer = arcpy.management.SelectLayerByAttribute(
            firePerimeterFC,
            "NEW_SELECTION",
            yearQuery
        )

        # Use that selection (layer object) when copying
        outputFC = f"fires_{year}"
        arcpy.management.CopyFeatures(yearsLayer, outputFC)

        print(f'Created output fire features for {year}')

        # Use search cursor to select fields of interest within each fire feature class
        with arcpy.da.SearchCursor(outputFC, [acresField, startdateField, enddateField]) as yearTotals:
            for yearCounts in yearTotals:
                if yearCounts[0]:
                    totalAcresBurntInYearCounter += yearCounts[0]
                if yearCounts[1] and yearCounts[2]:
                    totalBurnDaysInYearCounter += (yearCounts[2] - yearCounts[1]).days

        print(f"{year} had {totalAcresBurntInYearCounter:,.0f} acres burnt")
        print(f"{year} had {totalBurnDaysInYearCounter:,.0f} burn days")

        # Add fields to each created feature class
        arcpy.management.AddFields(outputFC, [
            [firesPercentageOfAcreageBurnt, dataType],
            [firesPercentageofDaysBurnt, dataType]
        ])

        print(f'Added new fields to {year} feature class')

        # Populate new fields with an update cursor
        with arcpy.da.UpdateCursor(outputFC, (firesPercentageOfAcreageBurnt, acresField,
                                              firesPercentageofDaysBurnt, startdateField,
                                              enddateField)) as cursor:
            for row in cursor:
                # Calculate percentage of year's total acres
                if totalAcresBurntInYearCounter > 0:
                    row[0] = (row[1] / totalAcresBurntInYearCounter) * 100
                else:
                    row[0] = 0

                # Calculate percentage of year's total days
                startDate = row[3]
                endDate = row[4]
                if startDate and endDate and totalBurnDaysInYearCounter > 0:
                    fireDays = (endDate - startDate).days
                    row[2] = (fireDays / totalBurnDaysInYearCounter) * 100
                else:
                    row[2] = 0

                cursor.updateRow(row)

        print(f'Populated new fields in {year} feature class')

        # Update summary table field values
        pOfAllAcres = (totalAcresBurntInYearCounter / totalAcresBurntCounter) * 100 if totalAcresBurntCounter > 0 else 0
        pOfAllDays = (totalBurnDaysInYearCounter / totalBurnDaysCounter) * 100 if totalBurnDaysCounter > 0 else 0

        # Insert a summary row into summary table
        with arcpy.da.InsertCursor(summaryTable,
                                   ["Year", "TotalAcres", "TotalDays", "PofAllAcres", "PofAllDays"]) as finalcursor:
            finalcursor.insertRow(
                (year, totalAcresBurntInYearCounter, totalBurnDaysInYearCounter, pOfAllAcres, pOfAllDays))

    print('Populated summary table successfully!')

except Exception as e:
    print(f"Failed to select fires from the given years: {e}")

finally:
    # Clean up
    arcpy.management.Delete(yearsLayer)
    # Delete cursor references
    del totalCountsCursor
    del totalCounts
    del yearTotals
    del yearCounts
    del row
    del cursor
    del finalcursor