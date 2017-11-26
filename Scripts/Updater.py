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
        self.hpad = 15
        self.wpad = 5

        self.xcode_opts = None
        self.sdk_over = None

        if os.path.exists("profiles.json"):
            self.profiles = json.load(open("profiles.json"))
        else:
            self.profiles = []
        self.selected_profile = None

        self.version_url = "https://github.com/corpnewt/Lilu-and-Friends/raw/master/Scripts/plugins.json"

        theJSON = json.load(open("plugins.json"))

        self.plugs = theJSON.get("Plugins", [])
        self.version = theJSON.get("Version", "0.0.0")
        self.checked_updates = False

        # Select default profile
        self._select_profile("default")

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
    def head(self, text = "Lilu And Friends", width = 55):
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

    def profile(self):
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        self.head("Profiles")
        print(" ")
        if not len(self.profiles):
            print("No profiles")
        else:
            ind = 0
            for option in self.profiles:
                ind += 1
                if self.selected_profile == option["Name"]:
                    pick = "[#]"
                else:
                    pick = "[ ]"
                extra = "1 kext " if len(option.get("Kexts", [])) == 1 else "{} kexts ".format(len(option.get("Kexts", [])))
                extra += "- Default build options " if option.get("Xcode", None) == None else "- \"{}\"".format(option.get("Xcode", None))
                extra += "- Default sdk" if option.get("SDK", None) == None else "- \"{}\"".format(option.get("SDK", None))
                en = "{} {}. {} - {}".format(pick, ind, option.get("Name", None), extra)
                if len(en) + self.wpad > self.w:
                    self.w = len(en) + self.wpad
                print(en)
        print(" ")
        print("S. Save Current Settings to Profile")
        print("R. Remove Selected Profile")
        print("N. Select None")
        print("M. Main Menu")
        print("Q. Quit")
        print(" ")
        menu = self.grab("Please make a selection:  ")

        if not len(menu):
            self.profile()
            return

        if menu[:1].lower() == "q":
            self.custom_quit()
        elif menu[:1].lower() == "m":
            return
        elif menu[:1].lower() == "n":
            for p in self.plugs:
                p["Picked"] = False
            self.selected_profile = None
            self.profile()
            return
        elif menu[:1].lower() == "r":
            # Remove the offending option
            for option in self.profiles:
                if option["Name"] == self.selected_profile:
                    self.profiles.remove(option)
                    break
            # Save to file
            json.dump(self.profiles, open("profiles.json", "w"), indent=2)
            self.selected_profile = None
            self.profile()
            return
        elif menu[:1].lower() == "s":
            self.save_profile()
            self.profile()
            return
        # Get numeric value
        try:
            menu = int(menu)
        except:
            # Not a number
            self.profile()
            return

        if menu > 0 and menu <= len(self.profiles):
            # Valid profile
            self._select_profile(self.profiles[menu-1]["Name"])
            self.profile()

    def _select_profile(self, profile_name):
        # Selects a profile by the passed name
        selected = None
        for pro in self.profiles:
            if pro["Name"].lower() == profile_name.lower():
                selected = pro
                break
        if not selected:
            return
        # Pick only the ones needed
        for p in self.plugs:
            p["Picked"] = True if p["Name"] in selected["Kexts"] else False
        # Set the rest of the options
        self.xcode_opts = selected.get("Xcode", None)
        self.selected_profile = selected.get("Name", None)
        self.sdk_over = selected.get("SDK", None)
        
    def save_profile(self):
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        self.head("Save to Profile")
        print(" ")
        kextlist = []
        for option in self.plugs:
            if "Picked" in option and option["Picked"] == True:
                kextlist.append(option["Name"])
        if len(kextlist):
            info = "Selected Kexts ({}):\n\n{}\n\n".format(len(kextlist), ", ".join(kextlist))
        else:
            info = "Selected Kexts (0):\n\nNone\n\n"
        if self.xcode_opts == None:
            info += "Xcodebuild Options:\n\nDefault\n\n"
        else:
            info += "Xcodebuild Options:\n\n{}\n\n".format(self.xcode_opts)
        if self.sdk_over == None:
            info += "SDK:\n\nDefault\n\n"
        else:
            info += "SDK:\n\n{}\n\n".format(self.sdk_over)
        info += "If a profile is named \"Default\" it will be loaded automatically\n\n"
        info += "P. Profile Menu\nM. Main Menu\nQ. Quit\n"
        print(info)
        menu = self.grab("Please type a name for your profile:  ")

        if not len(menu):
            self.save_profile()
            return
        
        if menu.lower() == "p":
            return
        elif menu.lower() == "q":
            self.custom_quit()
        elif menu.lower() == "m":
            self.main()
            return

        # We have a name
        for option in self.profiles:
            if option["Name"].lower() == menu.lower():
                # Updating
                option["Kexts"] = kextlist
                option["Xcode"] = self.xcode_opts
                option["SDK"] = self.sdk_over
                # Save to file
                json.dump(self.profiles, open("profiles.json", "w"), indent=2)
                self.selected_profile = menu
                return
        # Didn't find it
        new_pro = { "Name" : menu, "Kexts" : kextlist, "Xcode" : self.xcode_opts, "SDK" : self.sdk_over }
        self.profiles.append(new_pro)
        # Save to file
        json.dump(self.profiles, open("profiles.json", "w"), indent=2)
        self.selected_profile = menu

    def xcodeopts(self):
        self.resize(self.w, self.h)
        self.head("Xcode Options")
        print(" ")
        if not self.xcode_opts:
            print("Current Options:  Default")
        else:
            print("Current Options:  {}".format(self.xcode_opts))
        print(" ")
        print("C. Clear")
        print("M. Main Menu")
        print("S. SDK Override")
        print("Q. Quit")
        print(" ")
        menu = self.grab("Please type your build opts:  ")

        if not len(menu):
            self.xcodeopts()
            return
        if menu.lower() == "c":
            # Profile change!
            self.selected_profile = None
            self.xcode_opts = None
            self.xcodeopts()
            return
        if menu.lower() == "s":
            self.sdk_override()
            return
        elif menu.lower() == "m":
            return
        elif menu.lower() == "q":
            self.custom_quit()
        else:
            if not self.xcode_opts == menu:
                # Profile change!
                self.selected_profile = None
            self.xcode_opts = menu
        self.xcodeopts()

    def sdk_override(self):
        self.resize(self.w, self.h)
        self.head("SDK Overrides")
        print(" ")
        if not self.sdk_over:
            print("Current SDK:  Default")
        else:
            print("Current SDK:  {}".format(self.sdk_over))
        print(" ")
        print("X. Xcode Options")
        print("M. Main Menu")
        print("Q. Quit")
        print(" ")
        menu = self.grab("Please type your sdk override (macosx[##.##]):  ")

        if not len(menu):
            self.sdk_override()
            return
        if menu.lower() == "x":
            return
        elif menu.lower() == "m":
            self.main()
            return
        elif menu.lower() == "q":
            self.custom_quit()
        else:
            # Verify
            if not menu.lower().startswith("macosx"):
                self.sdk_override()
                return
            print("Valid")
            if not self.sdk_over == menu:
                # Profile change!
                self.selected_profile = None
            self.sdk_over = menu
        self.sdk_override()

    def need_update(self, new, curr):
        for i in range(len(curr)):
            if int(new[i]) < int(curr[i]):
                return False
            elif int(new[i]) > int(curr[i]):
                return True
        return False

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
                en = "{} {}. {} - {}".format(pick, ind, option["Name"], option["Desc"])
            else:
                en = "{} {}. {}".format(pick, ind, option["Name"])
            if len(en) + self.wpad > self.w:
                self.w = len(en) + self.wpad
            print(en)
        
        # Resize to fit
        self.h = self.hpad + len(self.plugs)
        self.resize(self.w, self.h)

        print(" ")
        print("B. Build Selected")
        print(" ")
        print("A. Select All")
        print("N. Select None")
        print("X. Xcodebuild Options")
        print("P. Profiles")
        print("Q. Quit")
        print(" ")
        menu = self.grab("Please make a selection:  ")

        if not len(menu):
            return
        
        if menu[:1].lower() == "q":
            self.custom_quit()
        elif menu[:1].lower() == "x":
            self.xcodeopts()
        elif menu[:1].lower() == "p":
            self.profile()
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
                    out = self.kb.build(plug, ind, len(build_list), self.xcode_opts, self.sdk_over)
                except Exception as e:
                    print(e)
                    out = ["", "An error occurred!", 1]
                if out == None:
                    success.append("    " + plug["Name"])
                else:
                    print(out[1])
                    fail.append("    " + plug["Name"])
            # Clean up temp
            print("Cleaning up...")
            self.kb._del_temp()
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
            # Profile change!
            self.selected_profile = None
            return
        elif menu[:1].lower() == "n":
            # Select none
            for plug in self.plugs:
                plug["Picked"] = False
            # Profile change!
            self.selected_profile = None
            return
        
        # First try to split
        menu = menu.replace(" ", "")
        menu_list = menu.split(",")
        for m in menu_list:
            # Get numeric value
            try:
                m = int(m)
            except:
                continue
            if m > 0 and m <= len(self.plugs):
                # Remove profile selection - as we've made changes
                self.selected_profile = None
                m -=1
                if "Picked" in self.plugs[m]:
                    if self.plugs[m]["Picked"]:
                        self.plugs[m]["Picked"] = False
                        continue
                self.plugs[m]["Picked"] = True
        return

# Create our main class, and loop - catching exceptions
up = Updater()
while True:
    try:
        up.main()
    except Exception as e:
        print(e)
        time.sleep(5)
