import subprocess
import plistlib
import os
import tempfile
import shutil
import datetime

class KextBuilder:

    def __init__(self):
        self.git = self._get_git()
        self.xcodebuild = self._get_xcodebuild()
        self.zip = self._get_zip()
        self.temp = None

    def _get_output(self, comm):
        c = None
        try:
            p = subprocess.Popen(comm, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            c = p.communicate()
            return (c[0].decode("utf-8"), c[1].decode("utf-8"), p.returncode)
        except:
            if c == None:
                return ("", "Command not found", 1)
            return (c[0].decode("utf-8"), c[1].decode("utf-8"), p.returncode)

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

    def _get_xcodebuild(self):
        # Returns the path to the xcodebuild binary
        return self._get_output(["which", "xcodebuild"])[0].split("\n")[0].split("\r")[0]

    def _get_git(self):
        # Returns the path to the git binary
        return self._get_output(["which", "git"])[0].split("\n")[0].split("\r")[0]
    
    def _get_zip(self):
        # Returns the path to the zip binary
        return self._get_output(["which", "zip"])[0].split("\n")[0].split("\r")[0]

    def _get_lilu_debug(self):
        # Downloads and compiles the latest lilu - then returns the path to it
        if not self._get_temp():
            return None
        os.chdir(self.temp)
        output = self._get_output([self.git, "clone", "https://github.com/vit9696/Lilu"])
        if not output[2]:
            exit(1)

    # Header drawing method
    def head(self, text = "Lilu Updater", width = 55):
        os.system("clear")
        print("  {}".format("#"*width))
        mid_len = int(round(width/2-len(text)/2)-2)
        middle = " #{}{}{}#".format(" "*mid_len, text, " "*((width - mid_len - len(text))-2))
        print(middle)
        print("#"*width)

    def _clean_up(self, output):
        print(output[1])
        if not self._del_temp():
            print("Temp not deleted!")
            print(self.temp)
        os.chdir(os.path.dirname(os.path.realpath(__file__)))

    def _get_lilu(self):
        if os.path.exists(self.temp + "/Lilu/build/Debug/Lilu.kext"):
            return self.temp + "/Lilu/build/Debug/Lilu.kext"
        print("Building Lilu:")
        # Download the debug version of lilu first
        if not os.path.exists(self.temp + "/Lilu"):
            # Only download if we need to
            print("    Downloading Lilu...")
            output = self._get_output([self.git, "clone", "https://github.com/vit9696/Lilu"])
            if not output[2] == 0:
                return None
        os.chdir("Lilu")
        print("    Building debug version...")
        output = self._get_output([self.xcodebuild, "-configuration", "Debug"])
        if not output[2] == 0:
            return None
        if os.path.exists(self.temp + "/Lilu/build/Debug/Lilu.kext"):
            return self.temp + "/Lilu/build/Debug/Lilu.kext"
        return None

    def build(self, plug, curr = None, total = None, ops = None, sdk = None):
        # Builds a kext
        # Gather info
        name       = plug["Name"]
        url        = plug["URL"]
        needs_lilu = plug.get("Lilu", False)
        folder     = plug.get("Folder", plug["Name"])
        prerun     = plug.get("Pre-Run", None)
        skip_dsym  = plug.get("Skip dSYM", True)

        return_val = None

        '''if total:
            self.head("Updating " + name + " ({} of {})".format(curr, total))
        else:
            self.head("Updating " + name)'''
        print(" ")
        if not self._get_temp():
            print("Something went wrong!")
            exit(1)
        os.chdir(self.temp)
        if needs_lilu:
            l = self._get_lilu()
        # From here - do all things relative
        if total:
            print("Building {} ({:,} of {:,})".format(name, curr, total))
        else:
            print("Building " + name + ":")
        if not os.path.exists(folder):
            print("    Downloading " + name + "...")
            # args = [self.git]
            # Split the args by space and stuff
            # args.extend(url.split())
            args = url.split()
            output = self._get_output(args)
            if not output[2] == 0:
                # self._clean_up(output)
                return output
        os.chdir(folder)
        if prerun:
            # Run this first
            output = self._get_output(prerun)
            if not output[2] == 0:
                # self._clean_up(output)
                return output
        if needs_lilu:
            # Copy in our beta kext
            output = self._get_output(["cp", "-R", l, "."])
            if not output[2] == 0:
                # self._clean_up(output)
                return output
        print("    Building release version...")
        xcode_args = [ self.xcodebuild ]
        if ops:
            print("    Using \"{}\"...".format(ops))
            xcode_args.extend(ops.split())
        else:
            xcode_args.extend(plug.get("Build Opts", []))
        # Make sure it builds in the local directory - but only if using -scheme
        xcode_args.append("BUILD_DIR=" + os.path.join(os.getcwd(), "build/"))
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
        output = self._get_output(xcode_args)

        if not output[2] == 0:
            if plug.get("Ignore Errors", False):
                print("    Build had errors - attempting to continue past the following:\n\n{}".format(output[1]))
                return_val = True
            else:
                # self._clean_up(output)
                return output

        os.chdir(plug.get("Build Dir", "./Build/Release"))
        info_plist = plistlib.readPlist(plug.get("Info", name + ".kext/Contents/Info.plist"))
        version = info_plist["CFBundleVersion"]
        print("Zipping...")
        file_name = name + "-" + version + "-{:%Y-%m-%d %H.%M.%S}.zip".format(datetime.datetime.now())
        zip_dir = plug.get("Zip", name+".kext")
        if type(zip_dir) is str:
            if not os.path.exists(zip_dir):
                return ["", "{} missing!".format(zip_dir), 1]
        zip_args = [self.zip, "-r", file_name]
        if type(zip_dir) is list:
            zip_args.extend(zip_dir)
        else:
            zip_args.append(zip_dir)
        if skip_dsym:
            zip_args.extend(["-x", "*.dSYM*"])
        output = self._get_output(zip_args)

        if not output[2] == 0:
            # self._clean_up(output)
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
        # Reset shell position
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        # Return None on success
        return (return_val, version)
