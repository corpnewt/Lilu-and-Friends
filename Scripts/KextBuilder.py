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
        try:
            p = subprocess.Popen(comm, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            c = p.communicate()
            return (c[0].decode("utf-8"), c[1].decode("utf-8"), p.returncode)
        except:
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
    def head(self, text = "Lilu Updater", width = 50):
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


    def build(self, plug, curr = None, total = None):
        # Builds a kext
        # Gather info
        name       = plug["Name"]
        url        = plug["URL"]
        needs_lilu = plug.get("Lilu", False)
        if "Folder" in plug:
            folder = plug["Folder"]
        else:
            folder = None

        if total:
            self.head("Updating " + name + " ({} of {})".format(curr, total))
        else:
            self.head("Updating " + name)
        print(" ")
        if not self._get_temp():
            print("Something went wrong!")
            exit(1)
        os.chdir(self.temp)
        if needs_lilu:
            print("Building Lilu:")
            # Download the debug version of lilu first
            print("    Downloading Lilu...")
            output = self._get_output([self.git, "clone", "https://github.com/vit9696/Lilu"])
            if not output[2] == 0:
                self._clean_up(output)
                return output
            os.chdir("Lilu")
            print("    Building debug version...")
            output = self._get_output([self.xcodebuild, "-configuration", "Debug"])
            if not output[2] == 0:
                self._clean_up(output)
                return output
        # From here - do all things relative
        print("Building " + name + ":")
        print("    Downloading " + name + "...")
        args = [self.git]
        # Split the args by space and stuff
        args.extend(url.split())
        output = self._get_output(args)
        if not output[2] == 0:
            self._clean_up(output)
            return output
        if folder:
            os.chdir(folder)
        else:
            os.chdir(name)
        if needs_lilu:
            # Copy in our beta kext
            output = self._get_output(["cp", "-R", self.temp + "/Lilu/build/Debug/Lilu.kext", "."])
            if not output[2] == 0:
                self._clean_up(output)
                return output
        print("    Building release version...")
        output = self._get_output([self.xcodebuild])
        if not output[2] == 0:
            self._clean_up(output)
            return output
        os.chdir(plug.get("Build Dir", "./Build/Release"))
        info_plist = plistlib.readPlist(plug.get("Info", name + ".kext/Contents/Info.plist"))
        version = info_plist["CFBundleVersion"]
        print("Zipping...")
        file_name = name + "-" + version + "-{:%Y-%m-%d %H.%M.%S}.zip".format(datetime.datetime.now())
        zip_dir = plug.get("Zip", name+".kext")
        output = self._get_output([self.zip, "-r", file_name, zip_dir])
        if not output[2] == 0:
            self._clean_up(output)
            return output
        zip_path = os.getcwd() + "/" + file_name
        print("Built " + name + " v" + version)
        dir_path = os.path.dirname(os.path.realpath(__file__))
        os.chdir(dir_path)
        os.chdir("../")
        kexts_path = os.getcwd() + "/Kexts"
        if not os.path.exists(kexts_path):
            os.mkdir(kexts_path)
        if not os.path.exists(kexts_path + "/" + name):
            os.mkdir(kexts_path + "/" + name)
        shutil.copy(zip_path, kexts_path + "/" + name)
        print("Cleaning up...")
        if not self._del_temp():
            print("Temp not deleted!")
            print(self.temp)
        print(" ")
        print("Done.")
        # Reset shell position
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        # Return None on success
        return None