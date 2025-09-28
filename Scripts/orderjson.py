import json
import os

j = "plugins.json"
# CD into the script's directory
os.chdir(os.path.dirname(os.path.realpath(__file__)))
# Check for the json file
if not os.path.exists(j):
    print("{} does not exist!".format(j))
    exit(1)
# Load the json
j_data = json.load(open(j, "r"))
# Reorganize it
j_data["Plugins"] = sorted(j_data["Plugins"], key=lambda x:(x["Name"].lower()))
# Dump the contents back
json.dump(j_data, open(j, "w"), indent=2, sort_keys=True)
# Done!
print("Done!")
exit(0)
