import subprocess
import plist
import os
import tempfile
import shutil
import datetime
import run
import glob
import xml.etree.ElementTree as ET

class KextBuilder:

    def __init__(self):
        self.r = run.Run()
        self.git = self._get_bin("git")
        self.xcodebuild = self._get_bin("xcodebuild")
        self.zip = self._get_bin("zip")
        self.temp = None
        self.debug = False
        self.fix_xib = "1060"

    def _del_temp(self):
        # Removes the saved temporary file
        if not self.temp:
            return True
        if os.path.exists(self.temp):
            shutil.rmtree(self.temp)
        return not os.path.exists(self.temp)

    def _get_temp(self):
        # Loads self.temp with a new temp folder location
        if self.temp and os.path.exists(self.temp):
            return self.temp
        self._del_temp()
        self.temp = tempfile.mkdtemp()
        return os.path.exists(self.temp)

    def _get_bin(self, bin_name):
        return self.r.run({"args":["which", bin_name]})[0].split("\n")[0].split("\r")[0]

    # Header drawing method
    def head(self, text = "Lilu Updater", width = 55):
        os.system("clear")
        print("  {}".format("#"*width))
        mid_len = int(round(width/2-len(text)/2)-2)
        middle = " #{}{}{}#".format(" "*mid_len, text, " "*((width - mid_len - len(text))-2))
        print(middle)
        print("#"*width)

    def _get_lilu(self):
        if os.path.exists(self.temp + "/Lilu/build/Debug/Lilu.kext"):
            return self.temp + "/Lilu/build/Debug/Lilu.kext"
        print("Building Lilu:")
        # Download the debug version of lilu first
        if not os.path.exists(self.temp + "/Lilu"):
            # Only download if we need to
            print("    Downloading Lilu...")
            if not self.r.run({"args":[self.git, "clone", "--depth", "1", "https://github.com/acidanthera/Lilu"], "stream" : self.debug})[2] == 0: return None
            # Also get the MacKernelSDK and copy it into our Lilu folder
            mac_kernel_sdk = self._get_sdk()
            if mac_kernel_sdk is None: return None
            if not self.r.run({"args":["rsync", "-ahP", mac_kernel_sdk, "./Lilu"], "stream" : self.debug})[2] == 0: return None
        cwd = os.getcwd()
        os.chdir("Lilu")
        print("    Building debug version...")
        if not self.r.run({"args":[self.xcodebuild, "-configuration", "Debug"], "stream" : self.debug})[2] == 0:
            os.chdir(cwd)
            return None
        os.chdir(cwd)
        if os.path.exists(self.temp + "/Lilu/build/Debug/Lilu.kext"):
            return self.temp + "/Lilu/build/Debug/Lilu.kext"
        return None

    def _get_sdk(self):
        if os.path.exists(self.temp + "/MacKernelSDK"):
            return self.temp + "/MacKernelSDK"
        print("    Downloading MacKernelSDK...")
        cwd = os.getcwd()
        os.chdir(self.temp)
        if not self.r.run({"args":[self.git, "clone", "--depth", "1", "https://github.com/acidanthera/MacKernelSDK"], "stream" : self.debug})[2] == 0:
            os.chdir(cwd)
            return None
        os.chdir(cwd)
        if os.path.exists(self.temp + "/MacKernelSDK"):
            return self.temp + "/MacKernelSDK"
        return None

    def _debug(self, string):
        return string.replace("Release 10.6","Debug").replace("Release","Debug").replace("release","debug").replace("RELEASE","DEBUG")

    def build(self, plug, curr = None, total = None, ops = None, sdk = None):
        # Builds a kext
        # Gather info
        name       = plug["Name"]
        url        = plug["URL"]
        needs_lilu = plug.get("Lilu", False)
        needs_sdk  = plug.get("MacKernelSDK", False)
        folder     = plug.get("Folder", plug["Name"])
        skip_phase = plug.get("Remove Phases", [])
        prebuild   = plug.get("Pre-Build", [])
        postbuild  = plug.get("Post-Build", [])
        skip_dsym  = plug.get("Skip dSYM", True)
        required   = plug.get("Required",[])
        skip_targ  = plug.get("Skip Targets",[])
        fix_xib    = plug.get("FixXib", False)
        build_opts = plug.get("Build Opts", [])
        build_dir  = plug.get("Build Dir", "./Build/Release")
        ignore_err = plug.get("Ignore Errors", False)
        p_info     = plug.get("Info", name + ".kext/Contents/Info.plist")
        zip_dir    = plug.get("Zip", name+".kext")
        debug      = plug.get("Debug", False) # Change to false later

        if debug:
            # we need to prep some stuff for debug builds
            for p in prebuild:
                if p.get("no_debug_replace"):
                    continue
                p["args"] = [self._debug(x) for x in p["args"]]
            for p in postbuild:
                if p.get("no_debug_replace"):
                    continue
                p["args"] = [self._debug(x) for x in p["args"]]
            build_opts = [self._debug(x) for x in build_opts]
            build_dir = self._debug(build_dir)
            if isinstance(zip_dir,list):
                zip_dir = [self._debug(x) for x in zip_dir]
            else:
                zip_dir = self._debug(zip_dir)
            name = name+" (Debug)"

        return_val = None

        print(" ")

        missing = []
        for x in required:
            if isinstance(x, list):
                m = [z for z in x if not len(self._get_bin(z))]
                if len(m) == len(x):
                    # Missing all of them in our optional list
                    missing.extend(x)
            else:
                if not len(self._get_bin(x)):
                    missing.append(x)
        if len(missing):
            return ("","Missing requirements to build {}:\n{}".format(name, ", ".join(missing)))

        if not self._get_temp():
            print("Something went wrong!")
            exit(1)
        os.chdir(self.temp)
        if needs_lilu:
            l = self._get_lilu()
            if l is None: return ("","Failed to get Lilu!",1)
        # From here - do all things relative
        if total:
            print("Building {} ({:,} of {:,})".format(name, curr, total))
        else:
            print("Building " + name + ":")
        if not os.path.exists(folder):
            print("    Downloading " + name + "...")
            # Split the args by space and stuff
            args = url.split()
            output = self.r.run({"args":args, "stream" : self.debug})
            if not output[2] == 0:
                return output
        os.chdir(folder)
        if (needs_lilu or needs_sdk):
            mac_kernel_sdk = self._get_sdk()
            if mac_kernel_sdk is None: return ("","Failed to get MacKernelSDK!",1)
        if len(skip_phase):
            print("    Removing Build Phases...")
        currtask = 0
        for task in skip_phase:
            # Iterate the files given, and remove the existing text from the buildPhases
            # section if they exist.  We can take either the id or the name (providing they)
            # both exist.  All compares are done case-insensitively
            currtask += 1
            f = task.get("path", "")
            if not os.path.exists(f):
                print("     - {} not found!".format(f))
                continue
            # Found our file - scrape it
            found_phases = False
            found_count  = 0
            temp_text = ""
            with open(f, "r") as x:
                for line in x:
                    phase_match = [x for x in task.get("phases",[]) if x.lower() in line.lower()]
                    if found_phases and len(phase_match):
                        # Primed and we found a skip
                        print("     - Found {} - skipping...".format(", ".join(phase_match)))
                        found_count += 1
                        continue
                    # If we *are* primed - we need to make sure that we only add phases that don't exist
                    # in our exception list - and if we hit ");" we need to unprime again.
                    if ");" in line and found_phases:
                        # Primed and we found the end - unprime
                        found_phases = False
                    # Check to see if we can prime last - to avoid pre-priming or something weird
                    if "buildphases" in line.lower():
                        found_phases = True
                    # Append the line
                    temp_text += line
            print("     - {} of {} phase{} skipped.".format(found_count, len(task.get("phases",[])), "" if len(task.get("phases",[])) == 1 else "s"))
            # Check if we found any phases, and if so - write the changes
            if found_count:
                print("     - Flushing changes to {}...".format(f))
                with open(f,"w") as x:
                    x.write(temp_text)
        if fix_xib:
            print("    Fixing Xibs...")
            # Scans for .xib files and ensure that the IBDocument.PluginDeclaredDependencies real value
            # is set to our fix_xib value
            for root, dirs, files in os.walk("."):
                for n in files:
                    if not n.lower().endswith(".xib"):
                        continue
                    print("    - Found {}".format(n))
                    # We have a .xib file - let's load it, check the values,
                    # make changes if needed, and save it
                    try:
                        changed = False
                        print("    --> Loading...")
                        tree = ET.parse(os.path.join(root, n))
                        r = tree.getroot()
                        # Let's see if we can find the value
                        for x in r[0]:
                            # Loop each item in the root's data, and look for IBDocument.PluginDeclaredDependencies key
                            # if found, check each element and if located, set the fix_xib value
                            if x.attrib.get("key","") == "IBDocument.PluginDeclaredDependencies":
                                for y in x:
                                    if y.tag == "integer" and "value" in y.attrib:
                                        # Set the value
                                        print("    --> Changing {} --> {}...".format(y.attrib["value"], self.fix_xib))
                                        y.set("value", self.fix_xib)
                                        changed = True
                        if changed:
                            # Write the changes
                            print("    --> Saving changes...")
                            fe = ET.tostring(r)
                            if isinstance(fe, bytes):
                                fe = fe.decode("utf-8")
                            with open(os.path.join(root, n), "w") as g:
                                g.write(fe)
                    except Exception as e:
                        print("    --> Failed!")
                        pass

        def path_replace(path): # Helper to replace pathing elements in pre and post-build
            return path.replace("[[scripts]]",sp).replace("[[kexts]]",kp).replace("[[cwd]]",cp)

        if len(prebuild):
            print("    Running Pre-Build Tasks ({})...".format(len(prebuild)))
        currtask = 0
        for task in prebuild:
            # Iterate the tasks, and run them as needed
            args = []
            currtask += 1
            # Format for the command should be:
            #
            # lang path [arg1, arg2, arg3, ...]
            # 
            # With environment vars set as needed
            #
            # lang = path to the calling binary if the path is a script
            # path = path to the target relative to our current dir
            # args = list of arguments
            # env  = environment variables to set
            # bail = to bail on errors - default is true

            # Also allow object replacement in the passed scripts
            # [[scripts]] = the path to the scripts folder
            # [[kexts]] = the path to the kexts folder
            # [[cwd]] = the current working directory

            # Build the arguments list
            if task.get("lang",None):
                args.append(task["lang"])
            sp = os.path.dirname(os.path.realpath(__file__))
            kp = os.path.dirname(sp)
            cp = os.getcwd()
            if isinstance(task.get("path"),list) and task["path"]:
                # We have multiple optional paths - let's find the first hit
                use_path = path_replace(task["path"][0])
                for path in task["path"]:
                    path = path_replace(path)
                    if os.path.exists(path): # Check if the adjusted path exists and save it
                        use_path = path
                        break
                args.append(use_path)
                task["path"] = use_path # Replace the original entry with the first match
            else: # It's not a list
                args.append(path_replace(task.get("path","")))
            for arg in task.get("args",[]):
                # Expand any pathing, then glob
                a = path_replace(arg)
                if "*" in a:
                    try:
                        # Glob!
                        a = glob.glob(a)
                    except:
                        pass
                if isinstance(a,list):
                    args.extend(a)
                else:
                    args.append(a)

            # Set the env vars if they exist
            if task.get("env", None):
                for e in task["env"]:
                    os.environ[e] = str(task["env"][e])

            # Set the task's name if exists, or use the basename of the path
            tname = task.get("name",os.path.basename(task.get("path","Unknown")))
            # Run the task
            print("     - Running task {} of {} - {}...".format(currtask, len(prebuild), tname))
            output = self.r.run({"args":args, "stream" : self.debug})
            if not output[2] == 0:
                output = (output[0], "     --> Pre-Build Task Failed!\n\n{}".format(output[1]), output[2])
                if task.get("bail", True):
                    return output
                if task.get("no_print"):
                    print("     --> Pre-Build Taks Failed!")
                else:
                    print(output[1])
                if not task.get("continue_on_fail"):
                    break
                
        if needs_lilu:
            # Copy in our debug kext
            output = self.r.run({"args":["rsync", "-ahP", l, "."], "stream" : self.debug})
            if not output[2] == 0:
                return output
        if needs_lilu or needs_sdk:
            # Copy in the sdk
            output = self.r.run({"args":["rsync", "-ahP", mac_kernel_sdk, "."], "stream" : self.debug})
            if not output[2] == 0:
                return output

        # Check target exclusions
        target_specs = []
        if len(skip_targ):
            print("    Verifying target exclusions...")
            output = self.r.run({"args":[self.xcodebuild, "-list"]})
            primed = False
            for line in output[0].split("\n"):
                line = line.strip()
                if line.lower() == "targets:":
                    primed = True
                    continue
                if not primed:
                    continue
                # Primed - let's see if we hit a break
                if not len(line):
                    break
                # Made it here, add the target if not in our list of targets
                if not line.lower() in [x.lower() for x in skip_targ]:
                    print("     - {} allowed".format(line))
                    target_specs.append("-target")
                    target_specs.append(line)
                else:
                    print("     - {} skipped".format(line))

        print("    Building {} version...".format("debug" if debug else "release"))
        xcode_args = [ self.xcodebuild ]
        if ops:
            print("    Using \"{}\"...".format(ops))
            xcode_args.extend(ops.split())
        else:
            xcode_args.extend(build_opts)
        # Add the targets if we have skips
        xcode_args.extend(target_specs)
        # Make sure it builds in the local directory - but only if using -scheme
        xcode_args.append("BUILD_DIR=" + os.path.join(os.getcwd(), "build/"))
        if debug:
            # Ensure we're building the Debug version
            if not "-configuration" in xcode_args:
                xcode_args.extend(["-configuration","Debug"])
            else:
                xcode_args = [self._debug(x) for x in xcode_args]
        if sdk:
            ind = -1
            for s in xcode_args:
                if s.lower() == "-sdk":
                    ind = xcode_args.index(s)
                    break
            if ind > -1:
                # Delete the -sdk and the next object
                del xcode_args[ind]
                del xcode_args[ind]
            xcode_args.extend(["-sdk", sdk])
            print("    SDK Override \"{}\"...".format(" ".join(xcode_args[1:])))
        output = self.r.run({"args":xcode_args, "stream" : self.debug})

        if not output[2] == 0:
            if ignore_err:
                print("    Build had errors - attempting to continue past the following:\n\n{}".format(output[1]))
                return_val = True
            else:
                return output

        if len(postbuild):
            print("    Running Post-Build Tasks ({})...".format(len(postbuild)))
        currtask = 0
        for task in postbuild:
            # Iterate the tasks, and run them as needed
            args = []
            currtask += 1
            # Format for the command should be:
            #
            # lang path [arg1, arg2, arg3, ...]
            # 
            # With environment vars set as needed
            #
            # lang = path to the calling binary if the path is a script
            # path = path to the target relative to our current dir
            # args = list of arguments
            # env  = environment variables to set
            # bail = to bail on errors - default is true

            # Also allow object replacement in the passed scripts
            # [[scripts]] = the path to the scripts folder
            # [[kexts]] = the path to the kexts folder
            # [[cwd]] = the current working directory

            # Build the arguments list
            if task.get("lang",None):
                args.append(task["lang"])
            sp = os.path.dirname(os.path.realpath(__file__))
            kp = os.path.dirname(sp)
            cp = os.getcwd()
            if isinstance(task.get("path"),list) and task["path"]:
                # We have multiple optional paths - let's find the first hit
                use_path = path_replace(task["path"][0])
                for path in task["path"]:
                    path = path_replace(path)
                    if os.path.exists(path): # Check if the adjusted path exists and save it
                        use_path = path
                        break
                args.append(use_path)
                task["path"] = use_path # Replace the original entry with the first match
            else: # It's not a list
                args.append(path_replace(task.get("path","")))
            for arg in task.get("args",[]):
                # Expand any pathing, then glob
                a = arg.replace("[[scripts]]",sp).replace("[[kexts]]",kp).replace("[[cwd]]",cp)
                if "*" in a:
                    try:
                        # Glob!
                        a = glob.glob(a)
                    except:
                        pass
                if isinstance(a,list):
                    args.extend(a)
                else:
                    args.append(a)

            # Set the env vars if they exist
            if task.get("env", None):
                for e in task["env"]:
                    os.environ[e] = str(task["env"][e])

            # Set the task's name if exists, or use the basename of the path
            tname = task.get("name",os.path.basename(task.get("path","Unknown")))
            # Run the task
            print("     - Running task {} of {} - {}...".format(currtask, len(postbuild), tname))
            output = self.r.run({"args":args, "stream" : self.debug})
            if not output[2] == 0:
                output = (output[0], "     --> Post-Build Task Failed!\n\n{}".format(output[1]), output[2])
                if task.get("bail", True):
                    return output
                if task.get("no_print"):
                    print("     --> Post-Build Taks Failed!")
                else:
                    print(output[1])
                if not task.get("continue_on_fail"):
                    break

        if debug and not os.path.exists(build_dir):
            # Even though we're debugging - try the release as well
            build_dir = plug.get("Build Dir", "./Build/Release")
        os.chdir(build_dir)
        with open(p_info,"rb") as f:
            info_plist = plist.load(f)
        version = info_plist["CFBundleVersion"]
        print("Zipping...")
        file_name = name + "-" + version + "-{:%Y-%m-%d %H.%M.%S}.zip".format(datetime.datetime.now())
        if isinstance(zip_dir,str):
            if not os.path.exists(zip_dir):
                return ["", "{} missing!".format(zip_dir), 1]
        zip_args = [self.zip, "-r", file_name]
        if not isinstance(zip_dir,list):
            # Make it a list
            zip_dir = [zip_dir]
        # Glob if needed
        for a in zip_dir:
            if "*" in a:
                # Try globbing
                try:
                    a = glob.glob(a)
                except:
                    pass
            if isinstance(a,list):
                zip_args.extend(a)
            else:
                zip_args.append(a)
        if skip_dsym and not debug:
            # Keep dSYM files for debugging
            zip_args.extend(["-x", "*.dSYM*"])
        output = self.r.run({"args":zip_args, "stream" : self.debug})

        if not output[2] == 0:
            return output
        zip_path = os.getcwd() + "/" + file_name
        print("Built " + name + " v" + version)
        dir_path = os.path.dirname(os.path.realpath(__file__))
        os.chdir(dir_path)
        os.chdir("../")
        kexts_path = os.getcwd() + "/Kexts"
        if not os.path.exists(kexts_path):
            os.mkdir(kexts_path)
        shutil.copy(zip_path, kexts_path)
        os.remove(zip_path)
        # Reset shell position
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        # Return None on success
        return (return_val, version)
