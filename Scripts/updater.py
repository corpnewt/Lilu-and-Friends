import sys, os

# Fix case differences
os.chdir(os.path.dirname(os.path.realpath(__file__)))
for file in os.listdir(os.getcwd()):
    if not file.lower().endswith(".py"):
        # Skip non-py files
        continue
    # Normalize the name to lower-case
    os.rename(os.path.join(os.getcwd(), file), os.path.join(os.getcwd(), file.lower()))

# Continue importing
import time, json, kextbuilder, tempfile, subprocess, shutil, base64, plist, random, re, datetime, run, kextupdater, downloader, zipfile, argparse, math

# Python-aware urllib stuff
if sys.version_info >= (3, 0):
    from urllib.request import urlopen
else:
    from urllib2 import urlopen

class Updater:

    def __init__(self):
        self.kb = kextbuilder.KextBuilder()
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        # Init our colors before we need to print anything
        if os.path.exists("colors.json"):
            self.colors_dict = json.load(open("colors.json"))
        else:
            self.colors_dict = {}
        self.colors   = self.colors_dict.get("colors", [])
        # Save colors in own file now
        if os.path.exists("colorsettings.json"):
            self.colorsettings = json.load(open("colorsettings.json"))
        else:
            self.colorsettings = {}
        # Get them
        self.hi_color = self.colorsettings.get("highlight", self.colors_dict.get("highlight", ""))
        self.er_color = self.colorsettings.get("error", self.colors_dict.get("error", ""))
        self.ch_color = self.colorsettings.get("changed", self.colors_dict.get("changed", ""))
        self.gd_color = self.colorsettings.get("success", self.colors_dict.get("success", ""))
        self.rt_color = self.colorsettings.get("reset", self.colors_dict.get("reset", ""))
        
        self.r = run.Run()
        self.k = kextupdater.KextUpdater()
        self.d = downloader.Downloader()

        # Order the colors quick
        if len(self.colors):
            reg = []
            bold = []
            for c in self.colors:
                if "bold" in c["name"].lower():
                    bold.append(c)
                else:
                    reg.append(c)
            reg.sort(key=lambda x: x["name"])
            bold.sort(key=lambda x: x["name"])
            reg.extend(bold)
            self.colors = reg
        if not os.path.exists("plugins.json"):
            self.head("Missing Files!")
            print(" ")
            print("Plugins.json doesn't exist!\n\nExiting...")
            print(" ")
            os._exit(1)

        if not os.path.exists("/Applications/Xcode.app") and not os.path.exists("/Applications/Xcode-beta.app"):
            self.head("Xcode Missing!")
            print(" ")
            print("Xcode is not installed in your /Applications folder!\n\nExiting...")
            print(" ")
            os._exit(1)

        out = self.r.run({"args":["xcodebuild", "-checkFirstLaunchStatus"]})
        if not out[2] == 0:
            self.head("Xcode First Launch")
            print(" ")
            self.r.run({"args" : ["xcodebuild", "-runFirstLaunch"], "sudo" : True, "stream" : True})
            print(" ")
            print("If everything ran correctly please relaunch the script.\n")
            os._exit(1)

        self.h = 0
        self.w = 0
        self.hpad = 32
        self.wpad = 8

        self.ee = base64.b64decode("TG9vayBzYXVzZSEgIEFuIGVhc3RlciBlZ2ch".encode("utf-8")).decode("utf-8")
        self.es = base64.b64decode("c2F1c2U=".encode("utf-8")).decode("utf-8")

        self.sdk_path = "/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs"
        self.sdk_version_plist = "/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Info.plist"
        
        # Account for Xcode-beta.app as well as Xcode.app
        if not os.path.exists(self.sdk_path):
            self.sdk_path = self.sdk_path.replace("Xcode.app", "Xcode-beta.app")
        if not os.path.exists(self.sdk_version_plist):
            self.sdk_version_plist = self.sdk_version_plist.replace("Xcode.app", "Xcode-beta.app")

        # Try to get our available SDKs
        self.sdk_list = self._get_sdk_list()

        self.xcode_opts = None
        self.sdk_over = None
        self.default_on_fail = False
        self.increment_sdk = False
        self.reveal = True
        self.kext_debug = False

        if os.path.exists("hashes.json"):
            self.hashes = json.load(open("hashes.json"))
        else:
            self.hashes = {}
        if self.hashes.get("update_wait", None) == None:
            self.hashes["update_wait"] = 172800

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

        # Migrate stuff
        self.migrate_profiles()

        # Make sure we have iasl
        self.iasl_url = "https://bitbucket.org/RehabMan/acpica/downloads/iasl.zip"
        self.iasl = self.check_iasl()

        # Setup the SDK url
        self.sdk_url = "https://github.com/phracker/MacOSX-SDKs/releases"
        self.remote_sdk_list = []

    def check_remote_sdk(self):
        self.remote_sdk_list = []
        self.head("Gathering Remote SDK List")
        print("")
        try:
            sdk = self.d.get_string(self.sdk_url)
        except:
            sdk = None
        if sdk == None:
            print("An error occurred :(")
            print("")
            print("You can manually download the SDKs from here:")
            print("")
            print(self.sdk_url)
            print("")
            self.grab("Press [enter] to continue...")
            return
        print("")
        # Got something - let's iterate
        for x in sdk.split("\n"):
            if not ".sdk.tar.xz" in x.lower() or not "a href" in x.lower():
                continue
            try:
                self.remote_sdk_list.append("https://github.com" + x.split('<a href="')[1].split('"')[0])
            except:
                pass
        return self.remote_sdk_list

    def check_iasl(self):
        target = os.path.join(os.path.dirname(os.path.realpath(__file__)), "iasl")
        if not os.path.exists(target):
            # Need to download
            self.head("Downloading iasl")
            print("")
            temp = tempfile.mkdtemp()
            try:
                self._download_and_extract(temp,self.iasl_url)
            except:
                print("An error occurred :(")
                print("")
                print("You can download the iasl binary from here:")
                print("")
                print(self.iasl_url)
                print("")
                print("Extract that zip, then place iasl in the Scripts folder in the")
                print("Lilu and Friends folder.")
                print("")
                self.grab("Press [enter] to continue...")
            shutil.rmtree(temp, ignore_errors=True)
        if os.path.exists(target):
            return target
        return None

    def _download_and_extract(self, temp, url):
        ztemp = tempfile.mkdtemp(dir=temp)
        zfile = os.path.basename(url)
        print("Downloading {}...".format(os.path.basename(url)))
        self.d.stream_to_file(url, os.path.join(ztemp,zfile), False)
        print(" - Extracting...")
        btemp = tempfile.mkdtemp(dir=temp)
        # Extract with built-in tools \o/
        with zipfile.ZipFile(os.path.join(ztemp,zfile)) as z:
            z.extractall(os.path.join(temp,btemp))
        script_dir = os.path.dirname(os.path.realpath(__file__))
        for x in os.listdir(os.path.join(temp,btemp)):
            if "iasl" in x.lower():
                # Found one
                print(" - Found {}".format(x))
                print("   - Chmod +x...")
                self.r.run({"args":["chmod","+x",os.path.join(btemp,x)]})
                print("   - Copying to {} directory...".format(os.path.basename(script_dir)))
                shutil.copy(os.path.join(btemp,x), os.path.join(script_dir,x))

    def migrate_profiles(self):
        # Helper method to migrate some profile info
        migrate = [
            {"find":["NvidiaGraphicsFixup","IntelGraphicsFixup","Shiki","CoreDisplayFixup","IntelGraphicsDVMTFixup"],"replace":["WhateverGreen"]},
            {"find":["BT4LEContiunityFixup"],"replace":["BT4LEContinuityFixup"]}
        ]
        changes = False
        for m in migrate:
            for profile in self.profiles:
                temp = [ x for x in profile["Kexts"] if x not in m["find"] ]
                if len(temp) != len(profile["Kexts"]):
                    # Something changed - add the replace kext(s) if they don't exist
                    [ temp.append(x) for x in m["replace"] if not x in temp ]
                    profile["Kexts"] = temp
                    changes = True
        # Check if anything changed - and apply
        if changes:
            # Save to file
            json.dump(self.profiles, open("profiles.json", "w"), indent=2)

    # Helper methods
    def grab(self, prompt):
        if sys.version_info >= (3, 0):
            return input(prompt)
        else:
            return str(raw_input(prompt))

    def cprint(self, message, **kwargs):
        strip_colors = kwargs.get("strip_colors", False)
        reset = u"\u001b[0m"
        # Requires sys import
        for c in self.colors:
            if strip_colors:
                message = message.replace(c["find"], "")
            else:
                message = message.replace(c["find"], c["replace"])
        if strip_colors:
            return message
        sys.stdout.write(message)
        print(reset)
        
    def _get_plist_dict(self, path):
        # Returns a dict of the plist data as a dict
        if not os.path.exists(path):
            print("{} doesn't exist!".format(path))
            return None
        try:
            with open(path,"rb") as f:
                d = plist.load(f)
        except Exception as e:
            print(str(e))
            return None
        return d

    def _get_sdk_min_version(self):
        sdk_min = None
        if os.path.exists(self.sdk_version_plist):
            try:
                sdk_plist = self._get_plist_dict(self.sdk_version_plist)
                sdk_min = sdk_plist["MinimumSDKVersion"]
            except:
                pass
        if not sdk_min:
            cur_vers = self._get_output(["sw_vers", "-productVersion"])[0]
            sdk_min = ".".join(cur_vers.split(".")[:2])
        return sdk_min

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

    def _get_sdk_list(self, sdk_path = None):
        # Sets our sdk list with what's currently available
        avail_sdk = []
        if not sdk_path:
            sdk_path = self.sdk_path
        if os.path.exists(sdk_path):
            sdk_list = os.listdir(sdk_path)
            for sdk in sdk_list:
                # Organize them by name and version
                if sdk.lower() == "macosx.sdk" or not "macos" in sdk.lower(): # Only allow macOS SDKs
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
                    os.readlink(os.path.join(sdk_path, sdk))
                    new_entry["default"] = True
                except:
                    pass
                avail_sdk.append(new_entry)
        return avail_sdk

    def _have_sdk(self, sdk_vers):
        # First break it into ##.## format
        sdk_vers = sdk_vers.lower().replace("macosx", "").replace(".sdk", "")
        # Refresh our sdk list
        self.sdk_list = self._get_sdk_list()
        for sdk in self.sdk_list:
            if sdk["version"] == sdk_vers:
                return True
        return False

    def _can_use_sdk(self, sdk_vers):
        # First break it into ##.## format
        sdk_vers = sdk_vers.lower().replace("macosx", "").replace(".sdk", "")
        if not self._compare_versions(sdk_vers, self._get_sdk_min_version()) == True:
            # sdk_verse is >= self._get_sdk_min_version()
            return True
        return False

    def _get_sdk_for_vers(self, sdk_vers):
        # First break into ##.## format
        sdk_vers = sdk_vers.lower().replace("macosx", "").replace(".sdk", "")
        # Refresh our sdk list
        self.sdk_list = self._get_sdk_list()
        for sdk in self.sdk_list:
            if sdk["version"] == sdk_vers:
                return sdk
        return None

    def _increment_sdk(self, sdk_vers, amount = 1):
        # First break into ##.## format
        sdk_vers = sdk_vers.lower().replace("macosx", "").replace(".sdk", "")
        while True:
            sdk_list = sdk_vers.split(".")
            sdk_new  = sdk_list[0] + "." + str(int(sdk_list[1])+amount)
            if self._compare_versions(sdk_new, self._highest_sdk()['version']) == False:
                # We're past the highest
                return None
            # Check if we actually have this sdk
            full_sdk = self._get_sdk_for_vers(sdk_new)
            if full_sdk:
                return full_sdk
            sdk_vers = sdk_new
        return sdk_new

    def _highest_sdk(self):
        # Returns the highest sdk that we have
        self._get_sdk_list()
        highest_sdk = self.sdk_list[0]
        for sdk in self.sdk_list:
            if self._compare_versions(sdk["version"], highest_sdk["version"]) == False:
                # Got a higher version, set it
                highest_sdk = sdk
        return highest_sdk

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
        len_text = self.cprint(text, strip_colors=True)
        mid_len = int(round(width/2-len(len_text)/2)-2)
        middle = " #{}{}{}#".format(" "*mid_len, len_text, " "*((width - mid_len - len(len_text))-2))
        middle = middle.replace(len_text, text + self.rt_color) # always reset just in case
        self.cprint(middle)
        print("#"*width)

    def resize(self, width, height):
        print('\033[8;{};{}t'.format(height, width))

    def custom_quit(self):
        self.resize(80,24)
        self.head("Lilu And Friends v"+self.gd_color+self.version)
        print("by CorpNewt\n")
        print("Thanks for testing it out, for bugs/comments/complaints")
        print("send me a message on Reddit, or check out my GitHub:\n")
        print("www.reddit.com/u/corpnewt")
        print("www.github.com/corpnewt\n")
        # Get the time and wish them a good morning, afternoon, evening, and night
        hr = datetime.datetime.now().time().hour
        if hr > 3 and hr < 12:
            print("Have a nice morning!\n\n")
        elif hr >= 12 and hr < 17:
            print("Have a nice afternoon!\n\n")
        elif hr >= 17 and hr < 21:
            print("Have a nice evening!\n\n")
        else:
            print("Have a nice night!\n\n")
        exit(0)
        os._exit(0)

    def custom_min_sdk(self):
        self.resize(80,24)
        self.head("Xcode MinimumSDKVersion")
        print(" ")
        print("Current MinimumSDKVersion:  {}".format(self._get_sdk_min_version()))
        print(" ")
        print("M. Main Menu")
        print("Q. Quit")
        print(" ")
        menu = self.grab("Please enter a new version in XX.XX format:  ")
        if not len(menu):
            self.custom_min_sdk()
            return
        
        if menu.lower() == "q":
            self.custom_quit()
        elif menu.lower() == "m":
            return

        # Check the format
        try:
            v_split = menu.split(".")
            majo = int(v_split[0])
            mino = int(v_split[1])
            vers = "{}.{}".format(majo, mino)
        except:
            self.head("Xcode MinimumSDKVersion")
            print(" ")
            self.cprint(self.er_color+"Invalid format!")
            print(" ")
            print("Must be in XX.XX format!")
            print(" ")
            time.sleep(3)
            self.custom_min_sdk()
            return

        # Check if we need to clear our SDK override
        if self.sdk_over and self._compare_versions(self.sdk_over.lower().replace("macosx", "").replace(".sdk", ""), vers):
            while True:
                sdk_vers = self.sdk_over.lower().replace("macosx", "").replace(".sdk", "")
                self.head(self.er_color+"SDK Conflict!")
                print(" ")
                print("The {} SDK Override doesn't meet the minimum!".format(sdk_vers))
                print(" ")
                m = self.grab("Would you like to clear it and continue? (y/n):  ")
                if m.lower() == "y":
                    self.sdk_over = None
                    self.selected_profile = None
                    break
                if m.lower() == "n":
                    self.custom_min_sdk()
                    return

        # Got a valid number - set it in the config
        # Create temp folder
        t = tempfile.mkdtemp()
        try:
            self.apply_min_sdk(vers, t)
        except:
            print("Something went wrong!")
            pass
        shutil.rmtree(t)

    def apply_min_sdk(self, version, temp):
        self.head("Updating Min SDK to {}".format(version))
        print(" ")
        if os.access(self.sdk_version_plist, os.W_OK):
            print("Have write permissions already...")
            # Can write to it normally
            print("Loading Info.plist...")
            sdk_plist = self._get_plist_dict(self.sdk_version_plist)
            print("Updating MinimumSDKVersion...")
            sdk_plist["MinimumSDKVersion"] = version
            print("Flushing changes...")
            with open(self.sdk_version_plist,"wb") as f:
                plist.dump(sdk_plist,f)
            print("Done!")
            time.sleep(3)
            return
        print("No write permissions, using temp folder...")
        # Need to use a temp folder and then sudo it back
        self.r.run({"args":["cp", self.sdk_version_plist, temp], "stream" : True})
        print("Loading Info.plist...")
        sdk_plist = self._get_plist_dict(os.path.join(temp, "Info.plist"))
        print("Updating MinimumSDKVersion...")
        sdk_plist["MinimumSDKVersion"] = version
        print("Writing Info.plist...")
        with open(os.path.join(temp,"Info.plist"),"wb") as f:
            plist.dump(sdk_plist,f)
        print("Copying back to {}...".format(self.sdk_version_plist))
        # Copy back over
        self.r.run({"args":["cp", os.path.join(temp, "Info.plist"), self.sdk_version_plist], "stream": True, "sudo" : True})

    def profile(self):
        self.resize(80,24)
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        self.head("Profiles")
        print(" ")
        if not len(self.profiles):
            self.cprint(self.er_color+"No profiles")
        else:
            ind = 0
            for option in self.profiles:
                ind += 1
                if self.selected_profile == option["Name"]:
                    pick = "[{}#{}]".format(self.ch_color, self.rt_color)
                else:
                    pick = "[ ]"
                extra = "1 kext " if len(option.get("Kexts", [])) == 1 else "{} kexts ".format(len(option.get("Kexts", [])))
                extra += "- Def build opts " if option.get("Xcode", None) == None else "- {}{}{}".format(self.ch_color, option.get("Xcode", None), self.rt_color)
                extra += "- Def sdk" if option.get("SDK", None) == None else "- {}{}{}".format(self.ch_color, option.get("SDK", None), self.rt_color)
                extra += " - {}DoF{}".format(self.ch_color, self.rt_color) if option.get("DefOnFail", False) else ""
                extra += " - {}iSDK{}".format(self.ch_color, self.rt_color) if option.get("IncrementSDK", False) else ""
                extra += " - {}Reveal{}".format(self.ch_color, self.rt_color) if option.get("Reveal", True) else ""
                en = "{} {}. {}{}{} - {}".format(pick, ind, self.hi_color, option.get("Name", None), self.rt_color, extra)
                #if len(self.cprint(en, strip_colors=True)) + self.wpad > self.w:
                testw = len(self.cprint(en, strip_colors=True)) + self.wpad
                self.w = testw if testw > 80 else 80
                self.cprint(en)
            self.h = ind+12 if ind+12 > 24 else 24
            self.resize(self.w, self.h)
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
            if self.save_profile() is not None:
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
        self.kext_debug = selected.get("Debug", False)
        # Revert SDK changes if there's an issue
        if self.sdk_over and not self._have_sdk(self.sdk_over):
            sdk_vers = self.sdk_over.lower().replace("macosx", "").replace(".sdk", "")
            self.head(self.er_color+"SDK Error"+self.rt_color+" Selecting: {}".format(profile_name))
            print(" ")
            print("Missing the {} SDK!".format(sdk_vers))
            print(" ")
            while True:
                ask = self.grab("Install now? (y/n):  ").lower()
                if ask == "n":
                    break
                elif ask == "y":
                    url = self.get_url_for_sdk_vers(sdk_vers)
                    if url:
                        test = self.download_and_install_sdk(url)
                        if test == True:
                            # Check if the sdk installed correctly
                            self._select_profile(profile_name)
                            return
                    else:
                        print("{} not available in remote SDK list...".format(sdk_vers))
                    break
            self.sdk_over = None
            self.selected_profile = None
            time.sleep(5)
        if self.sdk_over and not self._can_use_sdk(self.sdk_over):
            sdk_vers = self.sdk_over.lower().replace("macosx", "").replace(".sdk", "")
            self.head(self.er_color+"SDK Error"+self.rt_color+" Selecting: {}".format(profile_name))
            print(" ")
            print("{} is below Xcode's minimum!".format(sdk_vers))
            print(" ")
            while True:
                ask = self.grab("Set minimum to {} now? (y/n):  ".format(sdk_vers)).lower()
                if ask == "n":
                    break
                elif ask == "y":
                    t = tempfile.mkdtemp()
                    error = False
                    try:
                        self.apply_min_sdk(sdk_vers, t)
                    except:
                        print("Something went wrong!")
                        error = True
                    shutil.rmtree(t)
                    if not error:
                        self._select_profile(profile_name)
                        return
                    break
            self.sdk_over = None
            self.selected_profile = None
            time.sleep(5)
        self.default_on_fail = selected.get("DefOnFail", False)
        self.increment_sdk = selected.get("IncrementSDK", False)
        self.reveal = selected.get("Reveal", True)
        
    def save_profile(self):
        self.resize(80,24)
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        self.head("Save to Profile")
        pad = 39
        print(" ")
        kextlist = []
        for option in self.plugs:
            if "Picked" in option and option["Picked"] == True:
                kextlist.append(option["Name"])
        if len(kextlist):
            info = "Selected Kexts ({}):\n\n{}{}{}\n\n".format(len(kextlist), self.hi_color, "{}, {}".format(self.rt_color, self.hi_color).join(kextlist), self.rt_color)
        else:
            info = "Selected Kexts (0):\n\n{}None{}\n\n".format(self.er_color, self.rt_color)
            pad += 1
        if self.xcode_opts == None:
            info += "Xcodebuild Options:\n\nDefault\n\n"
        else:
            info += "Xcodebuild Options:\n\n{}{}{}\n\n".format(self.ch_color, self.xcode_opts, self.rt_color)
        if self.sdk_over == None:
            info += "SDK:\n\nDefault\n\n"
        else:
            info += "SDK:\n\n{}{}{}\n\n".format(self.ch_color, self.sdk_over, self.rt_color)
        info += "Defaults on Failure:\n\n{}{}{}\n\n".format(self.ch_color, self.default_on_fail, self.rt_color)
        info += "Reveal Kexts Folder On Success:\n\n{}{}{}\n\n".format(self.ch_color, self.reveal, self.rt_color)
        info += "Increment SDK on Fail:\n\n{}{}{}\n\n".format(self.ch_color, self.increment_sdk, self.rt_color)
        info += "Build Debug Kexts:\n\n{}{}{}\n\n".format(self.ch_color, self.kext_debug, self.rt_color)
        info += "If a profile is named \"{}Default{}\" it will be loaded automatically\n\n".format(self.hi_color, self.rt_color)
        info += "P. Profile Menu\nM. Main Menu\nQ. Quit\n"
        # Calculate quick height
        h = int(math.ceil((len(", ".join(kextlist))/80)+pad))
        self.resize(80,int(h))
        self.cprint(info)
        menu = self.grab("Please type a name for your profile:  ")

        if not len(menu):
            self.save_profile()
            return
        
        if menu.lower() == "p":
            return True
        elif menu.lower() == "q":
            self.custom_quit()
        elif menu.lower() == "m":
            self.main()
            return None

        # We have a name
        for option in self.profiles:
            if option["Name"].lower() == menu.lower():
                # Updating
                option["Kexts"] = kextlist
                option["Xcode"] = self.xcode_opts
                option["SDK"] = self.sdk_over
                option["DefOnFail"] = self.default_on_fail
                option["IncrementSDK"] = self.increment_sdk
                option["Reveal"] = self.reveal
                option["Debug"] = self.kext_debug
                # Save to file
                json.dump(self.profiles, open("profiles.json", "w"), indent=2)
                self.selected_profile = option["Name"]
                return
        # Didn't find it
        new_pro = { 
            "Name" : menu, 
            "Kexts" : kextlist, 
            "Xcode" : self.xcode_opts, 
            "SDK" : self.sdk_over, 
            "DefOnFail" : self.default_on_fail, 
            "IncrementSDK" : self. increment_sdk
            }
        self.profiles.append(new_pro)
        # Save to file
        json.dump(self.profiles, open("profiles.json", "w"), indent=2)
        self.selected_profile = menu

    def xcodeopts(self):
        self.resize(80, 24)
        self.head("Xcode Options")
        print(" ")
        if not self.xcode_opts:
            print("Build Options: Default")
        else:
            self.cprint("Build Options: {}{}{}".format(self.ch_color, self.xcode_opts, self.rt_color))
        if not self.sdk_over:
            print("SDK Options:   Default")
        else:
            self.cprint("SDK Options:   {}{}{}".format(self.ch_color, self.sdk_over, self.rt_color))
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
        self.resize(80, 24)
        self.head("SDK Overrides")
        print(" ")
        if not self.xcode_opts:
            print("Build Options: Default")
        else:
            self.cprint("Build Options: {}{}{}".format(self.ch_color, self.xcode_opts, self.rt_color))
        if not self.sdk_over:
            print("SDK Options:   Default")
        else:
            self.cprint("SDK Options:   {}{}{}".format(self.ch_color, self.sdk_over, self.rt_color))
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
                self.cprint(self.er_color+"You don't currently have a {} sdk.".format(menu))
                print(" ")
                while True:
                    ask = self.grab("Install now? (y/n):  ").lower()
                    if ask == "n":
                        self.sdk_override()
                        return
                    elif ask == "y":
                        name = menu.replace("macosx","")
                        url = self.get_url_for_sdk_vers(name)
                        if url:
                            test = self.download_and_install_sdk(url)
                            if test == True:
                                # Check if the sdk installed correctly
                                break
                        else:
                            print("{} not available in remote SDK list...".format(name))
                            print("")
                            self.grab("Press [enter] to continue...")
                        self.sdk_override()
                        return

            # We have it - let's make sure Xcode will use it
            if not self._can_use_sdk(menu):
                self.head("SDK Below Minimum!")
                print(" ")
                self.cprint(self.er_color+"Xcode is currently set to allow sdks of {} or higher.".format(self._get_sdk_min_version()))
                print("")
                name = menu.replace("macosx","")
                while True:
                    ask = self.grab("Set minimum to {} now? (y/n):  ".format(name)).lower()
                    if ask == "n":
                        self.sdk_override()
                        return
                    elif ask == "y":
                        t = tempfile.mkdtemp()
                        error = False
                        try:
                            self.apply_min_sdk(name, t)
                        except Exception as e:
                            print("Something went wrong!")
                            print(str(e))
                            print("")
                            error = True
                        shutil.rmtree(t)
                        if error:
                            self.grab("Press [enter] to continue...")
                            self.sdk_override()
                            return
                        break
            
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
            newjson = self.d.get_string(self.version_url, False)
        except:
            # Not valid json data
            self.cprint(self.er_color+"Error checking for updates (network issue)")
            return
        try:
            newjson_dict = json.loads(newjson)
        except:
            # Not valid json data
            self.cprint(self.er_color+"Error checking for updates (json data malformed or non-existent)")
            return
        check_version = newjson_dict.get("Version", "0.0.0")
        changelist    = newjson_dict.get("Changes", None)
        if self.version == check_version:
            # The same - return
            self.cprint("v{}{}{} is already current.".format(self.gd_color, self.version, self.rt_color))
            return
        # Split the version number
        try:
            v = self.version.split(".")
            cv = check_version.split(".")
        except:
            # not formatted right - bail
            self.cprint(self.er_color+"Error checking for updates (version string malformed)")
            return

        if not self.need_update(cv, v):
            self.cprint("v{}{}{} is already current.".format(self.gd_color, self.version, self.rt_color))
            return
    
        # We need to update
        while True:
            if changelist:
                # We have changes to display
                msg = "v{}{}{} is available (v{}{}{} installed)\n\nWhat's New:\n\n{}{}{}\n".format(
                    self.gd_color, 
                    check_version,
                    self.rt_color,
                    self.gd_color, 
                    self.version,
                    self.rt_color,
                    self.ch_color, 
                    changelist,
                    self.rt_color
                    )
            else:
                msg = "v{}{}{} is available (v{}{}{} installed)\n".format(
                    self.gd_color, 
                    check_version,
                    self.rt_color,
                    self.gd_color,
                    self.version,
                    self.rt_color)
            self.cprint(msg)
            up = self.grab("Update? (y/n):  ")
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
        print("Lilu and Friends has been updated!")
        print(" ")
        self.grab("Press [enter] to restart the script...")
        os.execv(sys.executable, ['python'] + sys.argv)

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
        self.resize(80, 24)
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

    def pick_color(self, name, var):
        self.resize(80, 24)
        self.head("{}{} Color".format(var, name))
        print(" ")
        c = [ x for x in self.colors if x["replace"] != "\u001b[0m" ]
        for i in range(len(c)):
            self.cprint("{}. {}{}".format(i+1, c[i]["find"], c[i]["name"]))
        self.resize(80, 24 if 24 > len(c)+12 else len(c)+12)
        print(" ")
        print(" ")
        print("C. Color Picker")
        print("M. Main Menu")
        print("Q. Quit")
        print(" ")
        menu = self.grab("Please pick a new {} color:  ".format(name.lower()))

        if not len(menu):
            self.color_picker()
            return
        if menu[:1].lower() == "m":
            self.main()
            return
        elif menu[:1].lower() == "q":
            self.custom_quit()
        elif menu[:1].lower() == "c":
            return
        try:
            menu = int(menu)
        except:
            self.color_picker()
            return
        menu -= 1
        if menu < 0 or menu >= len(c):
            self.pick_color()
            return
        # Have a valid thing now
        var = c[menu]["find"]
        self.colorsettings[name.lower()] = var
        if name.lower() == "highlight":
            self.hi_color = var
        elif name.lower() == "error":
            self.er_color = var
        elif name.lower() == "changed":
            self.ch_color = var
        elif name.lower() == "success":
            self.gd_color = var
        # Flush color changes
        self.colorsettings["highlight"] = self.hi_color
        self.colorsettings["error"]     = self.er_color
        self.colorsettings["changed"]   = self.ch_color
        self.colorsettings["success"]   = self.gd_color
        # Save to json
        json.dump(self.colorsettings, open("colorsettings.json", "w"), indent=2)

    def color_picker(self):
        self.resize(80, 24)
        c_list = [self.hi_color, self.ch_color, self.gd_color, self.er_color]
        n_list = ["Highlight", "Changed", "Success", "Error"]
        self.head("{}Color {}Picker".format(random.choice(c_list), random.choice(c_list)))
        print(" ")
        for i in range(len(c_list)):
            self.cprint("{}. {} {}Color".format(i+1, n_list[i], c_list[i]))
        self.resize(80, len(c_list)+11 if len(c_list)+11 > 24 else 24)
        print(" ")
        print("D. Reset to Defaults")
        print("M. Main Menu")
        print("Q. Quit")
        print(" ")
        menu = self.grab("Please pick a color to change:  ")

        if not len(menu):
            self.color_picker()
            return
        if menu[:1].lower() == "m":
            self.main()
            return
        elif menu[:1].lower() == "q":
            self.custom_quit()
        elif menu[:1].lower() == "d":
            self.hi_color = self.colorsettings["highlight"] = next((x["find"] for x in self.colors_dict["colors"] if x["find"] == "<bkb>"), "")
            self.er_color = self.colorsettings["error"]  = next((x["find"] for x in self.colors_dict["colors"] if x["find"] == "<rb>"), "")
            self.ch_color = self.colorsettings["changed"]  = next((x["find"] for x in self.colors_dict["colors"] if x["find"] == "<cb>"), "")
            self.gd_color = self.colorsettings["success"]  = next((x["find"] for x in self.colors_dict["colors"] if x["find"] == "<gb>"), "")
            json.dump(self.colorsettings, open("colorsettings.json", "w"), indent=2)
        try:
            menu = int(menu)
        except:
            self.color_picker()
            return
        menu -= 1
        if menu < 0 or menu >= len(c_list):
            self.color_picker()
            return
        # Have a valid thing now
        self.pick_color(n_list[menu], c_list[menu])
        self.color_picker()
        return

    def read_time(self, total):
        weeks   = int(total/604800)
        days    = int((total-(weeks*604800))/86400)
        hours   = int((total-(days*86400 + weeks*604800))/3600)
        minutes = int((total-(hours*3600 + days*86400 + weeks*604800))/60)
        seconds = int(total-(minutes*60 + hours*3600 + days*86400 + weeks*604800))
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

    def update_menu(self):
        self.resize(80,24)
        self.head("Update Menu")
        print(" ")
        print("Kext updates are only checked for those kexts with github repos")
        print("that have been built by Lilu and Friends at least once.\n")
        print("Launch Agent (LA) Info:\n")
        self.cprint("{}LA Installed:      {}{}".format(self.hi_color, self.ch_color, self.k.is_installed()))
        self.cprint("{}LA Loaded:         {}{}".format(self.hi_color, self.ch_color, self.k.is_loaded()))
        self.cprint("{}LA Check Interval: {}{}".format(self.hi_color, self.ch_color, self.read_time(self.hashes.get("update_wait", 172800))))
        print(" ")
        print("I. Install LA")
        print("L. Load LA")
        print("N. Uninstall LA")
        print("U. Unload LA")
        print(" ")
        print("M. Main Menu")
        print("Q. Quit")
        print(" ")
        print("Please pick an option - or type a new check interval with the")
        menu = self.grab("following format - N(w/d/h/m/s) - so 10 minutes would be 10m:  ")

        if not len(menu):
            self.update_menu()
            return
        if menu.lower() == "m":
            self.main()
            return
        elif menu.lower() == "q":
            self.custom_quit()
        elif menu.lower() == "i":
            self.k.install()
        elif menu.lower() == "l":
            self.k.load()
        elif menu.lower() == "n":
            self.k.uninstall()
        elif menu.lower() == "u":
            self.k.unload()

        # Check if we ahve a new time interval
        try:
            t = menu[-1].lower()
            n = int(menu[:-1])
            if t in ["w", "d", "h", "m", "s"]:
                # Valid stuffs
                t_adj = n
                if t == "w":
                    t_adj = n * 604800
                elif t == "d":
                    t_adj = n * 86400
                elif t == "h":
                    t_adj = n * 3600
                elif t == "m":
                    t_adj = n * 60

                self.hashes["update_wait"] = t_adj
        except:
            pass
        # Ensure settings are updated
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        json.dump(self.hashes, open("hashes.json", "w"), indent=2)
        self.update_menu()
        return
        # json.dump(self.hashes, open("hashes.json", "w"), indent=2)

    def build(self, headless = False):
        self.resize(80,24)
        # Building
        build_list   = []
        sdk_missing  = []
        sdk_too_high = []
        for plug in self.plugs:
            if plug.get("Picked",False):
                # Initialize overrides
                plug["xcode_opts"] = self.xcode_opts
                plug["sdk_over"]   = self.sdk_over
                plug["xcode_def_on_fail"] = False
                plug["inc_sdk_on_fail"] = False
                plug["Debug"] = self.kext_debug
                # Verify we can actually add it
                if not plug["sdk_over"]:
                    # No override - so we're checking for each kext individually
                    # Check for -sdk macosxXX.XX
                    low_opts = [ x.lower() for x in plug.get("Build Opts", []) ]
                    if "-sdk" in low_opts:
                        s_vers = None
                        try:
                            # Get the index of "-sdk" and
                            # then try to get the following
                            # index - which should be macosxXX.XX
                            s_ind  = low_opts.index("-sdk")
                            # strip the macosx and/or .sdk parts out
                            s_vers = low_opts[s_ind+1].replace("macosx", "").replace(".sdk", "")
                        except:
                            # Failed - skip
                            pass
                        if s_vers:
                            # We got a version, check it
                            if not self._have_sdk(s_vers):
                                sdk_missing.append(plug["Name"] + " - " + s_vers)
                                continue
                            if not self._can_use_sdk(s_vers):
                                sdk_too_high.append(plug["Name"] + " - " + s_vers)
                                continue
                build_list.append(plug)
        if len(sdk_missing) or len(sdk_too_high):
            while True:
                # We excluded kexts
                self.head(self.er_color+"Kexts Omitted!")
                if len(sdk_missing):
                    print(" ")
                    print("Kexts needing a missing sdk:\n")
                    self.cprint(self.er_color+"\n".join(sdk_missing))
                if len(sdk_too_high):
                    print(" ")
                    print("Kexts needing an sdk below Xcode's minimum:\n")
                    self.cprint(self.er_color+"\n".join(sdk_too_high))
                print(" ")
                # Find out if we need to give the user the option to continue
                if not headless and len(build_list):
                    prompt = "Continue building the remaining "
                    prompt = prompt + "1 kext? (y/n):  " if len(build_list) == 1 else prompt + "{} kexts? (y/n):  ".format(len(build_list))
                    m = self.grab(prompt)
                    if m.lower() == "y":
                        break
                    if m.lower() == "n":
                        return
                    continue
                # No other kexts to build
                if not headless:
                    self.grab("No other kexts in queue - press [enter] to return to the menu...")
                else:
                    print("No other kexts in queue.")
                return
        if not len(build_list):
            self.head(self.er_color+"WARNING")
            print(" ")
            print("Nothing to build - you must select at least one plugin!")
            time.sleep(3)
            return
        ind      = 0
        success  = []
        new_hash = []
        fail     = []
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
            success_string = ""
            if out[0] in [ None, True ]:
                # Format our output
                if out[0] == None:
                    success_string += "    " + self.hi_color + plug["Name"] + " v" + out[1] + self.rt_color
                elif out == True:
                    success_string += "    " + self.hi_color + plug["Name"] + " v" + out[1] + self.rt_color + " - " + self.er_color + "Errored, use with caution" + self.rt_color
                if plug["inc_sdk_on_fail"]:
                    success_string += " - {}{} SDK{}".format(self.ch_color, plug["sdk_over"].lower().replace("macosx", "").replace(".sdk", ""), self.rt_color)
                if plug["xcode_def_on_fail"]:
                    success_string += " - {}Xcode and SDK defaults{}".format(self.ch_color, self.rt_color)
                success.append(success_string)
                # Organize the latest hash info
                try:
                    hash_url = "http" + plug["URL"].lower().split("http")[1].split(" ")[0]
                    hash_val = self.k.get_hash(hash_url)
                    if hash_val:
                        new_hash.append({ "name" : plug["Name"], "url" : hash_url, "last_built" : hash_val })
                except:
                    pass
            else:
                self.cprint(self.er_color + out[1])
                if self.increment_sdk:
                    if plug["sdk_over"]:
                        new_sdk = self._increment_sdk(plug["sdk_over"])
                        if new_sdk:
                            self.cprint("\n{}Retrying {} with {} SDK.  Appended to end of list.\n".format(self.ch_color, plug["Name"], new_sdk['version']))
                            plug["sdk_over"] = "macosx" + new_sdk['version']
                            plug["inc_sdk_on_fail"] = True
                            build_list.append(plug)
                            # Back up the index
                            ind -= 1
                            continue
                if self.default_on_fail:
                    if plug["sdk_over"] or plug["xcode_opts"]:
                        self.cprint("\n{}Retrying {} with Xcode and SDK defaults.  Appended to end of list.\n".format(self.ch_color, plug["Name"]))
                        plug["sdk_over"]   = None
                        plug["xcode_opts"] = None
                        plug["xcode_def_on_fail"] = True
                        # Reset sdk increment
                        plug["inc_sdk_on_fail"] = False
                        build_list.append(plug)
                        # Back up the index
                        ind -=1
                        continue
                fail.append("    " + plug["Name"])
        
        # Flush the hashes
        b_kexts = self.hashes.get("built_kexts", [])
        overlap = [x["url"] for x in b_kexts for y in new_hash if x["url"].lower() == y["url"].lower()]
        # Add non-overlapping vars
        for b in b_kexts:
            if b["url"].lower() in overlap:
                continue
            new_hash.append(b)
        # Udate changes in json data and flush
        self.hashes["built_kexts"] = new_hash
        # Save to file
        json.dump(self.hashes, open("hashes.json", "w"), indent=2)

        # Clean up temp
        print("Cleaning up...")
        self.kb._del_temp()
        # Take time
        total_time = time.time() - start_time
        # Resize the window if need be
        h = 13 + (1 if not len(success) else len(success)) + (1 if not len(fail) else len(fail))
        h = h+2 if self.kext_debug else h
        h = h if h > 24 else 24
        self.resize(80,h)
        self.head("{} of {} Succeeded".format(len(success), total_kexts))
        print(" ")
        if self.kext_debug:
            self.cprint(" - {}Debug Kexts{} -\n".format(self.ch_color,self.rt_color))
        if len(success):
            self.cprint("{}Succeeded:{}\n\n{}".format(self.hi_color, self.rt_color, "\n".join(success)))
            # Only attempt if we reveal
            if self.reveal:
                try:
                    # Attempt to locate and open the kexts directory
                    os.chdir(os.path.dirname(os.path.realpath(__file__)))
                    os.chdir("../Kexts")
                    subprocess.Popen("open \"" + os.getcwd() + "\"", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                except:
                    pass
        else:
            self.cprint("{}Succeeded:{}\n\n    {}None".format(self.hi_color, self.rt_color, self.er_color))
        if len(fail):
            self.cprint("\n{}Failed:{}\n\n{}{}".format(self.hi_color, self.rt_color, self.er_color, "\n".join(fail)))
        else:
            self.cprint("\n{}Failed:{}\n\n    {}None".format(self.hi_color, self.rt_color, self.gd_color))
        print(" ")
        s = "second" if total_time == 1 else "seconds"
        print("Build took {}.\n".format(self.get_time(total_time)))
        if not headless:
            self.grab("Press [enter] to return to the main menu...")
        return

    def download_and_install_sdk(self, url):
        # Create a temp dir, download the file to it, extract the sdk,
        # then copy to the Xcode dir with admin privs
        self.head("Getting {} SDK".format(os.path.basename(url.replace(".sdk.tar.xz",""))))
        print("")
        temp = tempfile.mkdtemp()
        file_name = os.path.basename(url)
        sdk_name  = file_name.replace(".tar.xz","")
        file_path = os.path.join(temp,file_name)
        print("Downloading {}".format(file_name))
        try:
            self.d.stream_to_file(url, file_path)
            print("")
        except:
            pass
        if not os.path.exists(file_path):
            print("Failed to download :(")
            print("")
            self.grab("Press [enter] to return to the Install SDK menu...")
            shutil.rmtree(temp)
            return
        # Save our prior cwd and move to the temp folder
        cwd = os.path.dirname(os.path.realpath(__file__))
        os.chdir(temp)
        # Extract the sdk
        print("Extracting {}".format(file_name))
        out = self.r.run({"args":["tar","-xf",file_name]})
        if out[2] != 0:
            # Error occurred
            print("An error occurred during extraction...")
            print(out[1])
            print("")
            self.grab("Press [enter] to return to the Install SDK menu...")
            os.chdir(cwd)
            shutil.rmtree(temp)
            return
        # Remove the file
        print("Removing temp archive...")
        os.remove(file_path)
        # Extracted - let's make sure we can find the sdk
        if not os.path.exists(sdk_name) and os.path.isdir(sdk_name):
            print("{} not found after extraction...".format(sdk_name))
            print("")
            self.grab("Press [enter] to return to the Install SDK menu...")
            os.chdir(cwd)
            shutil.rmtree(temp)
            return
        os.chdir(cwd)
        # Found the extracted SDK - let's copy it over!
        print("Copying {} to {}...".format(sdk_name, self.sdk_path))
        out = self.r.run({"args":["rsync","-a","--append",os.path.join(temp,sdk_name),self.sdk_path],"sudo":True,"stream":True})
        if out[2] != 0:
            # Error occurred
            print("An error occurred while copying...")
            print(out[1])
            print("")
            self.grab("Press [enter] to return to the Install SDK menu...")
            shutil.rmtree(temp)
            return
        print("Cleaning up...")
        shutil.rmtree(temp)
        print("Re-detecting installed SDKs...")
        self.sdk_list = self._get_sdk_list()
        print("Done.")
        print("")
        return True

    def get_url_for_sdk_vers(self, vers):
        if self.remote_sdk_list == []:
            self.remote_sdk_list = self.check_remote_sdk()
        if self.remote_sdk_list == []:
            # Couldn't get the list
            return None
        for x in self.remote_sdk_list:
            # Get the name alone
            name = os.path.basename(x).replace(".sdk.tar.xz","").replace("MacOSX","")
            if name == vers:
                # Found it!
                return x
        return None

    def install_sdk(self):
        self.resize(80,24)
        if self.remote_sdk_list == []:
            self.remote_sdk_list = self.check_remote_sdk()
        if self.remote_sdk_list == []:
            # Couldn't get the list
            return
        self.head("Install SDKs")
        print("")
        print("Installed SDKs:")
        print("")
        print("\n".join([" - " + x["version"] for x in self.sdk_list]))
        print("")
        print("M. Main Menu")
        print("Q. Quit")

        h = 11+len(self.sdk_list)
        h = h if h > 24 else 24
        self.resize(80,h)

        add = self.grab("Please type the version number (eg. 10.10) of the SDK to install:  ")
        if not len(add):
            self.install_sdk()
            return
        if add.lower() == "m":
            return
        if add.lower() == "q":
            self.custom_quit()
        url = self.get_url_for_sdk_vers(add)
        if url:
            self.download_and_install_sdk(url)
            self.install_sdk()
            return
        self.head("SDK Error")
        print("")
        print("{} not found!".format(add))
        print("")
        self.grab("Press [enter] to return to the Install SDK menu....")
        self.install_sdk()

    def main(self):
        if not self.checked_updates:
            self.check_update()
            self.checked_updates = True
            # Select default profile
            self._select_profile("default")
        self.head("Lilu And Friends v"+self.gd_color+self.version)
        print(" ")
        # Print out options
        ind = 0
        for option in self.plugs:
            ind += 1
            if "Picked" in option and option["Picked"] == True:
                pick = "[{}#{}]".format(self.ch_color, self.rt_color)
            else:
                pick = "[ ]"
            if option.get("Desc", None):
                en = "{} {}. {}{}{} - {}".format(pick, ind, self.hi_color, option["Name"], self.rt_color, option["Desc"])
            else:
                en = "{} {}. {}{}{}".format(pick, ind, self.hi_color, option["Name"], self.rt_color)
            if len(self.cprint(en, strip_colors=True)) + self.wpad > self.w:
                self.w = len(self.cprint(en, strip_colors=True)) + self.wpad
            self.cprint(en)
        
        # Resize to fit
        self.h = self.hpad + len(self.plugs)
        self.resize(self.w, self.h)

        if not self.xcode_opts:
            print("Build Options:         Default")
        else:
            self.cprint("Build Options:         {}{}".format(self.ch_color, self.xcode_opts))
        if not self.sdk_over:
            print("SDK Options:           Default")
        else:
            self.cprint("SDK Options:           {}{}".format(self.ch_color, self.sdk_over))
        self.cprint("Increment SDK on Fail: {}{}".format(self.ch_color, self.increment_sdk))
        self.cprint("Defaults on Failure:   {}{}".format(self.ch_color, self.default_on_fail))
        self.cprint("Xcode Min SDK:         {}{}".format(self.ch_color, self._get_sdk_min_version()))
        self.cprint("Reveal Kexts Folder:   {}{}".format(self.ch_color, self.reveal))
        self.cprint("Build Debug Kexts:     {}{}".format(self.ch_color, self.kext_debug))
        if self.kb.debug:
            self.cprint("Debug:                 {}{}".format(self.ch_color, self.kb.debug))
        else:
            print("Debug:                 {}".format(self.kb.debug))

        print(" ")
        print("B.  Build Selected")
        print(" ")
        print("A.  Select All")
        print("N.  Select None")
        print("X.  Xcodebuild Options")
        print("S.  Update Xcode Min SDK")
        print("K.  Install SDKs")
        print("P.  Profiles")
        print("I.  Increment SDK on Fail")
        print("F.  Toggle Defaults on Failure")
        print("R.  Toggle Reveal Kexts Folder")
        print("D.  Toggle Debugging")
        print("TD. Toggle Building Debug Kexts")
        print("C.  Color Picker")
        print("U.  Update Menu")
        print("Q.  Quit")
        print(" ")
        menu = self.grab("Please make a selection:  ")

        if not len(menu):
            return
        
        if menu.lower() == "q":
            self.custom_quit()
        elif menu.lower() == "f":
            # Profile change!
            self.selected_profile = None
            self.default_on_fail ^= True
        elif menu.lower() == "i":
            # Profile change!
            self.selected_profile = None
            self.increment_sdk ^= True
        elif menu.lower() == "x":
            self.xcodeopts()
        elif menu.lower() == self.es:
            self.animate()
        elif menu.lower() == "p":
            self.profile()
        elif menu.lower() == "c":
            self.color_picker()
        elif menu.lower() == "d":
            self.kb.debug ^= True
        elif menu.lower() == "td":
            # Profile change!
            self.selected_profile = None
            self.kext_debug ^= True
        elif menu.lower() == "r":
            # Profile change!
            self.selected_profile = None
            self.reveal ^= True
        elif menu.lower() == "s":
            self.custom_min_sdk()
        elif menu.lower() == "k":
            self.install_sdk()
        elif menu.lower() == "u":
            self.update_menu()
        elif menu.lower() == "b":
            self.build()
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
        
        # Split args using regex
        menu_list = re.findall(r"[\w']+", menu)

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


if __name__ == '__main__':
    # Setup the cli args
    parser = argparse.ArgumentParser(prog="Run.command", description="Lilu And Friends - a Kext Builder by CorpNewt")
    parser.add_argument("-p", "--profile", help="sets the PROFILE to use - takes a name as an argument - must be setup in the gui.  Any other settings can override those passed by the profile", nargs="+")
    parser.add_argument("-k", "--kexts", help="a comma delimited list of kexts to build", nargs="+")
    parser.add_argument("-s", "--sdk", help="sets the SDK override to use (macosx##.## or ##.## format)")
    parser.add_argument("-x", "--xcodeopts", help="sets the xcode build options to use", nargs="+")
    parser.add_argument("-i", "--increment", help="increments the SDK on a failed build", action="store_true")
    parser.add_argument("-d", "--defaults", help="sets xcode defaults on failed build", action="store_true")
    parser.add_argument("-r", "--avoid-reveal", help="avoid revealing the Kexts folder on build completion", action="store_true")

    args = parser.parse_args()

    # Create our main class, and loop - catching exceptions
    up = Updater()
    
    if len(sys.argv) == 1:
        # No extra args - let's open the interactive mode
        while True:
            try:
                up.main()
            except Exception as e:
                print(e)
                time.sleep(5)

    # At this point - we have at least one arg - that means we're running
    # in non-interactive mode
    if args.profile:
        prof = " ".join(args.profile)
        up._select_profile(prof)
    if args.kexts:
        # Iterate the kexts and select only those included (and found)
        pluglist = [x.lower() for x in " ".join(args.kexts).split(",")]
        for plug in up.plugs:
            if plug["Name"].lower() in pluglist:
                plug["Picked"] = True
            else:
                plug["Picked"] = False
    if args.sdk:
        up.sdk_over = args.sdk
    if args.xcodeopts:
        xcodeopts = " ".join(args.xcodeopts)
        up.xcode_opts = args.xcodeopts
    if args.increment:
        up.increment_sdk = True
    if args.defaults:
        up.default_on_fail = True
    if args.avoid_reveal:
        up.reveal = False
    # Try to build!
    up.build(True)
