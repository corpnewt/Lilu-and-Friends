import sys
import os
import time
import json
import KextBuilder
import tempfile
import subprocess
import shutil
import base64
import plistlib

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
            print(" ")
            print("Plugins.json doesn't exist!\n\nExiting...")
            print(" ")
            os._exit(1)

        if not os.path.exists("/Applications/Xcode.app"):
            self.head("Xcode Missing!")
            print(" ")
            print("Xcode is not installed in your /Applications folder!\n\nExiting...")
            print(" ")
            os._exit(1)

        out = self._run_command("xcodebuild -checkFirstLaunchStatus", True)
        if not out[2] == 0:
            self.head("Xcode First Launch")
            print(" ")
            self._stream_output("sudo xcodebuild -runFirstLaunch", True)
            print(" ")
            print("If everything ran correctly please relaunch the script.\n")
            os._exit(1)

        self.h = 0
        self.w = 0
        self.hpad = 18
        self.wpad = 5

        self.ee = base64.b64decode("TG9vayBzYXVzZSEgIEFuIGVhc3RlciBlZ2ch".encode("utf-8")).decode("utf-8")
        self.es = base64.b64decode("c2F1c2U=".encode("utf-8")).decode("utf-8")

        self.sdk_path = "/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs"
        self.sdk_version_plist = "/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Info.plist"

        self.sdk_min_version = None
        if os.path.exists(self.sdk_version_plist):
            try:
                sdk_plist = plistlib.readPlist(self.sdk_version_plist)
                self.sdk_min_version = sdk_plist["MinimumSDKVersion"]
            except:
                pass
        if not self.sdk_min_version:
            cur_vers = self._get_output(["sw_vers", "-productVersion"])[0]
            self.sdk_min_version = ".".join(cur_vers.split(".")[:2])

        # Try to get our available SDKs
        self.sdk_list = []
        if os.path.exists(self.sdk_path):
            sdk_list = os.listdir(self.sdk_path)
            for sdk in sdk_list:
                # Organize them by name and version
                if sdk.lower() == "macosx.sdk":
                    # The default - so we're not sure what version
                    continue
                # Add some info
                new_entry = { 
                    "name"    : sdk,
                    "default" : False,
                    "version" : sdk.lower().replace("macosx", "").replace(".sdk", "")
                }
                try:
                    # This only works on aliases - so it'll fail for anything that's
                    # not linked to MacOSX.sdk
                    os.readlink(os.path.join(self.sdk_path, sdk))
                    new_entry["default"] = True
                except:
                    pass
                self.sdk_list.append(new_entry)

        self.xcode_opts = None
        self.sdk_over = None
        self.default_on_fail = False

        if os.path.exists("profiles.json"):
            self.profiles = json.load(open("profiles.json"))
        else:
            self.profiles = []
        self.selected_profile = None

        self.version_url = "https://raw.githubusercontent.com/corpnewt/Lilu-And-Friends/master/Scripts/plugins.json"

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

    def _stream_output(self, comm, shell = False):
        output = ""
        try:
            if shell and type(comm) is list:
                comm = " ".join(comm)
            if not shell and type(comm) is str:
                comm = comm.split()
            p = subprocess.Popen(comm, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1, universal_newlines=True)
            
            while True:
                cur = p.stdout.read(1)
                if(not cur):
                    break
                sys.stdout.write(cur)
                output += cur
                sys.stdout.flush()

            return output
        except:
            return output

    def _run_command(self, comm, shell = False):
        c = None
        try:
            if shell and type(comm) is list:
                comm = " ".join(comm)
            if not shell and type(comm) is str:
                comm = comm.split()
            p = subprocess.Popen(comm, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            c = p.communicate()
            return (c[0].decode("utf-8"), c[1].decode("utf-8"), p.returncode)
        except:
            if c == None:
                return ("", "Command not found!", 1)
            return (c[0].decode("utf-8"), c[1].decode("utf-8"), p.returncode)


    def _compare_versions(self, vers1, vers2):
        # Helper method to compare ##.## strings and determine
        # if vers1 is <= vers2
        #
        # vers1 < vers2 = True
        # vers1 = vers2 = None
        # vers1 > vers2 = False
        #
        try:
            v1_parts = vers1.split(".")
            v2_parts = vers2.split(".")
        except:
            # Formatted wrong - return None
            return None
        for i in range(len(v1_parts)):
            if int(v1_parts[i]) < int(v2_parts[i]):
                return True
            elif int(v1_parts[i]) > int(v2_parts[i]):
                return False
        # Never differed - return None, must be equal
        return None

    def _have_sdk(self, sdk_vers):
        # First break it into ##.## format
        sdk_vers = sdk_vers.lower().replace("macosx", "").replace(".sdk", "")
        for sdk in self.sdk_list:
            if sdk["version"] == sdk_vers:
                return True
        return False

    def _can_use_sdk(self, sdk_vers):
        # First break it into ##.## format
        sdk_vers = sdk_vers.lower().replace("macosx", "").replace(".sdk", "")
        if not self._compare_versions(sdk_vers, self.sdk_min_version) == True:
            # sdk_verse is >= self.sdk_min_version
            return True
        return False

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
        self.head("Lilu And Friends v"+self.version)
        print("by CorpNewt\n")
        print("Thanks for testing it out, for bugs/comments/complaints")
        print("send me a message on Reddit, or check out my GitHub:\n")
        print("www.reddit.com/u/corpnewt")
        print("www.github.com/corpnewt\n")
        print("Have a nice day/night!\n\n")
        os._exit(0)

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
                extra += "- Def build opts " if option.get("Xcode", None) == None else "- \"{}\"".format(option.get("Xcode", None))
                extra += "- Def sdk" if option.get("SDK", None) == None else "- \"{}\"".format(option.get("SDK", None))
                extra += " - DoF" if option.get("DefOnFail", False) else ""
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
        self.default_on_fail = selected.get("DefOnFail", False)
        
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
        info += "Defaults on Failure:\n\n{}\n\n".format(self.default_on_fail)
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
                option["DefOnFail"] = self.default_on_fail
                # Save to file
                json.dump(self.profiles, open("profiles.json", "w"), indent=2)
                self.selected_profile = option["Name"]
                return
        # Didn't find it
        new_pro = { "Name" : menu, "Kexts" : kextlist, "Xcode" : self.xcode_opts, "SDK" : self.sdk_over, "DefOnFail" : self.default_on_fail }
        self.profiles.append(new_pro)
        # Save to file
        json.dump(self.profiles, open("profiles.json", "w"), indent=2)
        self.selected_profile = menu

    def xcodeopts(self):
        self.resize(self.w, self.h)
        self.head("Xcode Options")
        print(" ")
        if not self.xcode_opts:
            print("Build Options: Default")
        else:
            print("Build Options: {}".format(self.xcode_opts))
        if not self.sdk_over:
            print("SDK Options:   Default")
        else:
            print("SDK Options:   {}".format(self.sdk_over))
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
        if not self.xcode_opts:
            print("Build Options: Default")
        else:
            print("Build Options: {}".format(self.xcode_opts))
        if not self.sdk_over:
            print("SDK Options:   Default")
        else:
            print("SDK Options:   {}".format(self.sdk_over))
        print(" ")
        print("C. Clear")
        print("X. Xcode Options")
        print("M. Main Menu")
        print("Q. Quit")
        print(" ")
        menu = self.grab("Please type your sdk override (macosx[##.##]):  ")

        if not len(menu):
            self.sdk_override()
            return
        if menu.lower() == "c":
            # Profile change!
            self.selected_profile = None
            self.sdk_over = None
            self.sdk_override()
            return
        elif menu.lower() == "x":
            self.xcodeopts()
            return
        elif menu.lower() == "m":
            self.main()
            return
        elif menu.lower() == "q":
            self.custom_quit()
        else:
            # Verify
            if not menu.lower().startswith("macosx"):
                # doesn't start with macosx - let's see if it fits the ##.## format
                try:
                    int_stuff = list(map(int, menu.split(".")))
                    if not len(int_stuff) == 2:
                        # Too many parts
                        self.sdk_override()
                        return
                    # set it to macosx##.## now
                    menu = "macosx" + menu
                except:
                    # not ##.## format - skip
                    self.sdk_override()
                    return

            # Got one - let's make sure we have it
            if not self._have_sdk(menu):
                self.head("Missing SDK!")
                print(" ")
                print("You don't currently have a {} sdk.".format(menu))
                print("You can visit the following site to download more sdks:\n")
                print("https://github.com/phracker/MacOSX-SDKs")
                print(" ")
                self.grab("Press [enter] to continue...")
                self.sdk_override()
                return

            # We have it - let's make sure Xcode will use it
            if not self._can_use_sdk(menu):
                self.head("SDK Below Minimum!")
                print(" ")
                print("Xcode is currently set to allow sdks of {} or higher.".format(self.sdk_min_version))
                print("You can edit the MinimumSDKVersion property in the Info.plist located at:\n")
                print(self.sdk_version_plist)
                print("\nto update this setting.")
                print(" ")
                self.grab("Press [enter] to continue...")
                self.sdk_override()
                return
            
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
        # Checks against https://raw.githubusercontent.com/corpnewt/Lilu-And-Friends/master/Scripts/plugins.json to see if we need to update
        self.head("Checking for Updates")
        print(" ")
        try:
            newjson = self._get_string(self.version_url)
        except:
            # Not valid json data
            print("Error checking for updates (network issue)")
            return
        try:
            newjson_dict = json.loads(newjson)
        except:
            # Not valid json data
            print("Error checking for updates (json data malformed or non-existent)")
            return
        check_version = newjson_dict.get("Version", "0.0.0")
        changelist    = newjson_dict.get("Changes", None)
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
            if changelist:
                # We have changes to display
                msg = "v{} is available (v{} installed)\nWhat's New: {}\n\nUpdate? (y/n):  ".format(check_version, self.version, changelist)
            else:
                msg = "v{} is available (v{} installed)\n\nUpdate? (y/n):  ".format(check_version, self.version)
            up = self.grab(msg)
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

    def get_time(self, t):
        # A helper function to make a readable string between two times
        weeks   = int(t/604800)
        days    = int((t-(weeks*604800))/86400)
        hours   = int((t-(days*86400 + weeks*604800))/3600)
        minutes = int((t-(hours*3600 + days*86400 + weeks*604800))/60)
        seconds = int(t-(minutes*60 + hours*3600 + days*86400 + weeks*604800))
        msg = ""
        
        if weeks > 0:
            msg += "1 week, " if weeks == 1 else "{:,} weeks, ".format(weeks)
        if days > 0:
            msg += "1 day, " if days == 1 else "{:,} days, ".format(days)
        if hours > 0:
            msg += "1 hour, " if hours == 1 else "{:,} hours, ".format(hours)
        if minutes > 0:
            msg += "1 minute, " if minutes == 1 else "{:,} minutes, ".format(minutes)
        if seconds > 0:
            msg += "1 second, " if seconds == 1 else "{:,} seconds, ".format(seconds)

        if msg == "":
            return "0 seconds"
        else:
            return msg[:-2]

    def animate(self):
        self.head("Entirely Required")
        print(" ")
        pad = count = 0
        padmax = 29
        right = True
        while count <= 100:
            count += 1
            if right:
                pad += 1
                if pad > padmax:
                    right = False
            else:
                pad -= 1
                if pad < 0:
                    pad = 0
                    right = True
            sys.stdout.write(" "*pad + self.ee + "\r")
            time.sleep(.1)

    def main(self):
        if not self.checked_updates:
            self.check_update()
            self.checked_updates = True
        self.head("Lilu And Friends v"+self.version)
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

        if not self.xcode_opts:
            print("Build Options:       Default")
        else:
            print("Build Options:       {}".format(self.xcode_opts))
        if not self.sdk_over:
            print("SDK Options:         Default")
        else:
            print("SDK Options:         {}".format(self.sdk_over))
        print("Defaults on Failure: {}".format(self.default_on_fail))

        print(" ")
        print("B. Build Selected")
        print(" ")
        print("A. Select All")
        print("N. Select None")
        print("X. Xcodebuild Options")
        print("P. Profiles")
        print("F. Toggle Defaults on Failure")
        print("Q. Quit")
        print(" ")
        menu = self.grab("Please make a selection:  ")

        if not len(menu):
            return
        
        if menu[:1].lower() == "q":
            self.custom_quit()
        elif menu[:1].lower() == "f":
            # Profile change!
            self.selected_profile = None
            self.default_on_fail ^= True
        elif menu[:1].lower() == "x":
            self.xcodeopts()
        elif menu.lower() == self.es:
            self.animate()
        elif menu[:1].lower() == "p":
            self.profile()
        elif menu[:1].lower() == "b":
            # Building
            build_list = []
            for plug in self.plugs:
                if "Picked" in plug and plug["Picked"] == True:
                    # Initialize overrides
                    plug["xcode_opts"] = self.xcode_opts
                    plug["sdk_over"]   = self.sdk_over
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
            # Take time
            start_time = time.time()
            total_kexts = len(build_list)
            self.head("Building 1 kext") if len(build_list) == 1 else self.head("Building {} kexts".format(len(build_list)))
            while len(build_list):
                plug = build_list.pop(0)
                ind += 1
                try:
                    out = self.kb.build(plug, ind, total_kexts, plug["xcode_opts"], plug["sdk_over"])
                except Exception as e:
                    print(e)
                    out = ["", "An error occurred!", 1]
                if out == None:
                    success.append("    " + plug["Name"])
                elif out == True:
                    success.append("    " + plug["Name"] + " (Build errored, but continued.  Use with caution)")
                else:
                    print(out[1])
                    if self.default_on_fail:
                        if plug["sdk_over"] or plug["xcode_opts"]:
                            print("\nRetrying {} with Xcode and SDK defaults.  Appended to end of list.\n".format(plug["Name"]))
                            plug["sdk_over"]   = None
                            plug["xcode_opts"] = None
                            build_list.append(plug)
                            # Back up the index
                            ind -=1
                            continue
                    fail.append("    " + plug["Name"])
            # Clean up temp
            print("Cleaning up...")
            self.kb._del_temp()
            # Take time
            total_time = time.time() - start_time
            self.head("{} of {} Succeeded".format(len(success), total_kexts))
            print(" ")
            if len(success):
                print("Succeeded:\n\n{}".format("\n".join(success)))
                try:
                    # Attempt to locate and open the kexts directory
                    os.chdir(os.path.dirname(os.path.realpath(__file__)))
                    os.chdir("../Kexts")
                    subprocess.Popen("open \"" + os.getcwd() + "\"", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                except:
                    pass
            else:
                print("Succeeded:\n\n    None")
            if len(fail):
                print("\nFailed:\n\n{}".format("\n".join(fail)))
            else:
                print("\nFailed:\n\n    None")
            print(" ")
            s = "second" if total_time == 1 else "seconds"
            print("Build took {}.\n".format(self.get_time(total_time)))
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
