# Prepare shift Attendance with pick_reach_final.csv file

# Download the shift schedule and rename file to "Attendance"](https://)

# import pandas as pd
# from numpy import nan

# # Load the Attendance CSV file
# attendance_df = pd.read_csv("Attendance.csv")

# # Keep only required columns
# attendance_df = attendance_df[["Name", "Shift Start"]].rename(columns={"Name": "Names"})

# # Convert Shift Start to datetime time
# attendance_df["Shift Start"] = pd.to_datetime(attendance_df["Shift Start"], format="%H:%M").dt.time

# # Define time window
# start_time = pd.to_datetime("18:30").time()
# end_time = pd.to_datetime("23:00").time()

# # Filter rows within the time range
# attendance_df_filtered = attendance_df[
#     (attendance_df["Shift Start"] >= start_time) &
#     (attendance_df["Shift Start"] <= end_time)
# ]

# # Sort so earliest shift start comes first per name
# attendance_df_filtered = attendance_df_filtered.sort_values(by="Shift Start", ascending=True)

# # Remove duplicates, keeping earliest shift start
# attendance_df_cleaned = attendance_df_filtered.drop_duplicates(subset="Names", keep="first")

# # Reset index
# attendance_df_cleaned = attendance_df_cleaned.reset_index(drop=True)

# # Save cleaned data
# attendance_df_cleaned.to_csv("attendance_cleaned.csv", index=False)

# # Display result
# print(attendance_df_cleaned)


##### Section 1 ###########
# Loading the Attendance.csv file and cleaning 

import pandas as pd

attendance_df = pd.read_csv("Attendance.csv")

attendance_df = attendance_df[["Alias", "Name", "Shift Start"]].rename(columns={"Name": "Names"})

# Convert safely
attendance_df["Shift Start"] = pd.to_datetime(
    attendance_df["Shift Start"],
    errors="coerce"
)

# Drop invalid
attendance_df = attendance_df.dropna(subset=["Shift Start"])

# Extract only time for filtering
attendance_df["Shift Time"] = attendance_df["Shift Start"].dt.time

start_time = pd.to_datetime("18:30").time()
end_time = pd.to_datetime("23:00").time()

attendance_df_filtered = attendance_df[
    (attendance_df["Shift Time"] >= start_time) &
    (attendance_df["Shift Time"] <= end_time)
]

attendance_df_filtered = attendance_df_filtered.sort_values("Shift Time")

attendance_df_cleaned = attendance_df_filtered.drop_duplicates(
    subset="Names",
    keep="first"
).reset_index(drop=True)

attendance_df_cleaned.to_csv("attendance_cleaned.csv", index=False)

print(attendance_df_cleaned)


########## section 2 #####

# Loading the pick_reach_final.csv file which helps to identify the process path for each person

# Attendance with Path 
import pandas as pd

# Load datasets
attendance_df = pd.read_csv("attendance_cleaned.csv")
pick_reach_df = pd.read_csv("pick_reach_final.csv")

# Standardize Names column (safety)
attendance_df["Names"] = attendance_df["Names"].str.strip()
pick_reach_df["Names"] = pick_reach_df["Names"].str.strip()

# LEFT JOIN: keep all attendance names
merged_df = pd.merge(
    attendance_df,
    pick_reach_df,
    on="Names",
    how="left"
)

# Keep only required columns
final_df = merged_df[["Alias","Names", "Path", "JPH"]]

# Remove duplicates just in case
final_df = final_df.drop_duplicates().reset_index(drop=True)

# Save final dataset
final_df.to_csv("attendance_with_pick_reach.csv", index=False)

# Display result
print(final_df)


####### Section 3 #######
# Removing persons using the loaded VTO.csv file. 
# VTO 
import pandas as pd

# Load datasets
final_df = pd.read_csv("attendance_with_pick_reach.csv")
vto_df = pd.read_csv("VTO.csv")

# Standardize columns (remove spaces and lowercase for safety)
final_df["Alias"] = final_df["Alias"].str.strip().str.lower()
vto_df["Employee Login"] = vto_df["Employee Login"].str.strip().str.lower()

# Remove employees that appear in the VTO list
cleaned_df = final_df[~final_df["Alias"].isin(vto_df["Employee Login"])]

# 🔹 Sort by Path column
cleaned_df = cleaned_df.sort_values(by="Path")

# Reset index
cleaned_df = cleaned_df.reset_index(drop=True)

# Save updated dataset
cleaned_df.to_csv("attendance_without_vto.csv", index=False)

# Display result
print(cleaned_df)