import sys
import os
import time
import json
import KextBuilder
import tempfile
import subprocess
import shutil

# Python-aware urllib stuff
if sys.version_info >= (3, 0):
    from urllib.request import urlopen
else:
    from urllib2 import urlopen

class Updater:

    def __init__(self):
        self.kb = KextBuilder.KextBuilder()
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        if not os.path.exists("plugins.json"):
            self.head("Missing Files!")
            print("Plugins.json doesn't exist!  Exiting...")
            exit(1)

        self.h = 0
        self.w = 0

        self.version_url = "https://github.com/corpnewt/Lilu-and-Friends/raw/master/Scripts/plugins.json"

        theJSON = json.load(open("plugins.json"))

        self.plugs = theJSON.get("Plugins", [])
        self.version = theJSON.get("Version", "0.0.0")
        self.checked_updates = False

    # Helper methods
    def grab(self, prompt):
        if sys.version_info >= (3, 0):
            return input(prompt)
        else:
            return str(raw_input(prompt))

    def _get_string(self, url):
        response = urlopen(url)
        CHUNK = 16 * 1024
        bytes_so_far = 0
        total_size = int(response.headers['Content-Length'])
        chunk_so_far = "".encode("utf-8")
        while True:
            chunk = response.read(CHUNK)
            bytes_so_far += len(chunk)
            #self._progress_hook(response, bytes_so_far, total_size)
            if not chunk:
                break
            chunk_so_far += chunk
        return chunk_so_far.decode("utf-8")

    def _progress_hook(self, response, bytes_so_far, total_size):
        percent = float(bytes_so_far) / total_size
        percent = round(percent*100, 2)
        sys.stdout.write("Downloaded {:,} of {:,} bytes ({:.2f}%)\r".format(bytes_so_far, total_size, percent))

    def _get_output(self, comm):
        try:
            p = subprocess.Popen(comm, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            c = p.communicate()
            return (c[0].decode("utf-8"), c[1].decode("utf-8"), p.returncode)
        except:
            return (c[0].decode("utf-8"), c[1].decode("utf-8"), p.returncode)

    def _get_git(self):
        # Returns the path to the git binary
        return self._get_output(["which", "git"])[0].split("\n")[0].split("\r")[0]

    # Header drawing method
    def head(self, text = "Lilu And Friends", width = 50):
        os.system("clear")
        print("  {}".format("#"*width))
        mid_len = int(round(width/2-len(text)/2)-2)
        middle = " #{}{}{}#".format(" "*mid_len, text, " "*((width - mid_len - len(text))-2))
        print(middle)
        print("#"*width)

    def resize(self, width, height):
        print('\033[8;{};{}t'.format(height, width))

    def custom_quit(self):
        self.resize(self.w, self.h)
        self.head("Lilu And Friends")
        print("by CorpNewt\n")
        print("Thanks for testing it out, for bugs/comments/complaints")
        print("send me a message on Reddit, or check out my GitHub:\n")
        print("www.reddit.com/u/corpnewt")
        print("www.github.com/corpnewt\n")
        print("Have a nice day/night!\n\n")
        exit(0)

    def need_update(self, new, curr):
        if new[0] < curr[0]:
            return False
        if new[0] > curr[0]:
            return True
        if new[1] < curr[1]:
            return False
        if new[1] > curr[1]:
            return True
        if new[2] < curr[2]:
            return False
        if new[2] > curr[2]:
            return True

    def check_update(self):
        # Checks against https://github.com/corpnewt/Lilu-and-Friends/raw/master/Scripts/plugins.json to see if we need to update
        self.head("Checking for Updates")
        print(" ")
        newjson = self._get_string(self.version_url)
        try:
            newjson_dict = json.loads(newjson)
        except:
            # Not valid json data
            print("Error checking for updates (json data malformed or non-existent)")
            return
        check_version = newjson_dict.get("Version", "0.0.0")
        if self.version == check_version:
            # The same - return
            print("v{} is already current.".format(self.version))
            return
        # Split the version number
        try:
            v = self.version.split(".")
            cv = check_version.split(".")
        except:
            # not formatted right - bail
            print("Error checking for updates (version string malformed)")
            return

        if not self.need_update(cv, v):
            print("v{} is already current.".format(self.version))
            return
    
        # We need to update
        while True:
            up = self.grab("v{} is available (v{} installed)\n\nUpdate? (y/n):  ".format(check_version, self.version))
            if up[:1].lower() in ["y", "n"]:
                break
        if up[:1].lower() == "n":
            print("Updating cancelled.")
            return
        # Update
        # Create temp folder
        t = tempfile.mkdtemp()
        g = self._get_git()
        # Clone into that folder
        os.chdir(t)
        output = self._get_output([g, "clone", "https://github.com/corpnewt/Lilu-and-Friends"])
        if not output[2] == 0:
            if os.path.exists(t):
                shutil.rmtree(t)
            print(output[1])
            os.chdir(os.path.dirname(os.path.realpath(__file__)))
            os.chdir("../")
            return
        # We've got the repo cloned
        # Move them over
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        os.chdir("../")
        p = subprocess.Popen("rsync -av \"" + t + "/Lilu-and-Friends/\" " + "\"" + os.getcwd() + "\"", shell=True)
        p.wait()
        p = subprocess.Popen("chmod +x \"" + os.getcwd() + "/Run.command\"", shell=True)
        p.wait()
        # Remove the old temp
        if os.path.exists(t):
            shutil.rmtree(t)
        self.head("Updated!")
        print(" ")
        print("Lilu and Friends has been updated!\nPlease restart the script to see the changes.")
        print(" ")
        self.grab("Press [enter] to quit...")
        exit(0)            


    def main(self):
        if not self.checked_updates:
            self.check_update()
            self.checked_updates = True
        # Resize to fit
        self.h = 12 + len(self.plugs)
        self.w = int(self.h*2.5)
        self.resize(self.w, self.h)
        self.head("Lilu And Friends")
        print(" ")
        # Print out options
        ind = 0
        for option in self.plugs:
            ind += 1
            if "Picked" in option and option["Picked"] == True:
                pick = "[#]"
            else:
                pick = "[ ]"
            if option.get("Desc", None):
                print("{} {}. {} - {}".format(pick, ind, option["Name"], option["Desc"]))
            else:
                print("{} {}. {}".format(pick, ind, option["Name"]))
        print(" ")
        print("B. Build Selected")
        print(" ")
        print("A. Select All")
        print("N. Select None")
        print("Q. Quit")
        print(" ")
        menu = self.grab("Please make a selection:  ")

        if not len(menu):
            return
        
        if menu[:1].lower() == "q":
            self.custom_quit()
        elif menu[:1].lower() == "b":
            # Building
            build_list = []
            for plug in self.plugs:
                if "Picked" in plug and plug["Picked"] == True:
                    build_list.append(plug)
            if not len(build_list):
                self.head("WARNING")
                print(" ")
                print("Nothing to build - you must select at least one plugin!")
                time.sleep(3)
                return
            ind = 0
            success = []
            fail    = []
            for plug in build_list:
                ind += 1
                try:
                    out = self.kb.build(plug, ind, len(build_list))
                except Exception as e:
                    print(e)
                    self.kb._del_temp()
                    out = 1
                if out == None:
                    success.append("    " + plug["Name"])
                else:
                    fail.append("    " + plug["Name"])
            self.head("{} of {} Succeeded".format(len(success), len(build_list)))
            print(" ")
            if len(success):
                print("Succeeded:\n\n{}".format("\n".join(success)))
            else:
                print("Succeeded:\n\n    None")
            if len(fail):
                print("\nFailed:\n\n{}".format("\n".join(fail)))
            else:
                print("\nFailed:\n\n    None")
            print(" ")
            self.grab("Press [enter] to return to the main menu...")
            return
                
        elif menu[:1].lower() == "a":
            # Select all
            for plug in self.plugs:
                plug["Picked"] = True
            return
        elif menu[:1].lower() == "n":
            # Select none
            for plug in self.plugs:
                plug["Picked"] = False
            return
        
        # Get numeric value
        try:
            menu = int(menu)
        except:
            return
        if menu > 0 and menu <= len(self.plugs):
            menu -=1
            if "Picked" in self.plugs[menu]:
                if self.plugs[menu]["Picked"]:
                    self.plugs[menu]["Picked"] = False
                    return
            self.plugs[menu]["Picked"] = True
        return

# Create our main class, and loop - catching exceptions
up = Updater()
while True:
    try:
        up.main()
    except Exception as e:
        print(e)
        time.sleep(5)
