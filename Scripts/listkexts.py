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
# Build a list of kexts - starting with *
kext_list = "Currently Builds {:,} Kext{}:\n\n".format(len(j_data["Plugins"]),"" if len(j_data["Plugins"])==1 else "s")
for k in j_data["Plugins"]:
    kext_list += "* {}\n".format(k["Name"])
print(kext_list)
exit(0)
