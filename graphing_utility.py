# quick and primitive tool to merge packet latency output files to be graphed

import csv

# dyanmic changes
exp = "exp1"

# static file names
folder_structure = ".\\Documents\\Main\\Final Export Folder Y3856355\\Simulator_Files\\"+exp+"\\"
f1 = folder_structure+exp+"_out_packet_latencies_FIFO.csv"
f2 = folder_structure+exp+"_out_packet_latencies_EDF.csv"
fmerge = folder_structure+exp+"_merge_packet_latencies.csv"

# open new file
f3 = open(fmerge, "w", newline='')
writer = csv.writer(f3)

# read data
with open(f1) as f:
    data1 = f.read().splitlines()
with open(f2) as f:
    data2 = f.read().splitlines()

# write headings
writer.writerow(["FIFO_"+data1[0], "EDF_"+data2[0]])

# get data the same size & strip heading
minlen = min(len(data1), len(data2))
data1 = data1[1:minlen]
data2 = data2[1:minlen]
print("New Data length:", len(data1), len(data2))
merged = []

# write merged data
for i in range(len(data1)):
    writer.writerow([data1[i], data2[i]])

# finish up
f3.close()

print("Done")
