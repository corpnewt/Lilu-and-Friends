import os, time, json, sys, re, plistlib
sys.path.append(os.path.abspath(os.path.dirname(os.path.realpath(__file__))))
import run, reveal

class KextUpdater:

    def __init__(self):
        self.json_file = "hashes.json"
        self.update_min = 60
        self.r = run.Run()
        self.re = reveal.Reveal()
        self.plist = "com.corpnewt.LiluAndFriends.plist"
        self.install_path = os.path.expanduser("~/Library/LaunchAgents/" + self.plist)
        self.script_path = os.path.realpath(__file__)

    def is_installed(self):
        return os.path.exists(self.install_path)

    def is_loaded(self):
        out = self.r.run({"args":["/bin/launchctl", "list"]})
        if not out[2] == 0:
            return False
        try:
            proc = [x for x in out[0].split("\n") if self.plist.lower() in x.lower()]
            if len(proc):
                return True
        except:
            pass
        return False

    def install(self):
        if os.path.exists(self.install_path):
            self.unload()
            self.uninstall()
        # Build the dict
        p = {
            "Label" : self.plist,
            "ProgramArguments" : [
                "/usr/bin/python",
                os.path.realpath(__file__)
            ],
            "RunAtLoad" : True
        }
        plistlib.writePlist(p, self.install_path)
        self.load()

    def uninstall(self):
        try:
            self.unload()
        except:
            pass
        if os.path.exists(self.install_path):    
            os.remove(self.install_path)

    def unload(self):
        self.r.run({"args":["/bin/launchctl", "unload", self.install_path]})

    def load(self):
        self.r.run({"args":["/bin/launchctl", "load", self.install_path]})

    def start(self):
        update_wait = 10
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        while True:
            time.sleep(update_wait)
            # Starts the countdown and update check
            if not os.path.exists(self.json_file):
                # No data - bail
                exit(1)
            # Load the json data and parse for our stuff
            j_data = json.load(open(self.json_file))
            # Get update frequency, and updated kexts
            update_wait = j_data.get("update_wait", None)
            try:
                update_wait = int(update_wait)
            except:
                update_wait = None
            if update_wait == None or update_wait < self.update_min: # Can't go under a minute - too much
                # Bail
                exit(1)
            # Get our hash list
            built = j_data.get("built_kexts", [])
            # Check kexts!
            updates = self.check_updates(built)
            if not len(updates):
                # Nothing needed
                continue
            # Got updates
            self.re.notify("Kext Updates!", ", ".join([x["name"] for x in updates]))
            # Flush the hashes
            overlap = [x["url"] for x in built for y in updates if x["url"].lower() == y["url"].lower()]
            # Add non-overlapping vars
            for b in built:
                if b["url"].lower() in overlap:
                    continue
                updates.append(b)
            # Udate changes in json data and flush
            j_data["built_kexts"] = updates
            # Save to file
            json.dump(j_data, open(self.json_file, "w"), indent=2)

    def get_hash(self, url):
        out_hash = self.r.run({"args" : ["git", "ls-remote", url]})
        if out_hash[2] != 0:
            # git failed
            return None
        try:
            head = next( x for x in out_hash[0].split("\n") if "HEAD" in x )
            return head.split("\t")[0].lower()
        except:
            pass
        return None

    def check_updates(self, kext_list):
        ups = []
        for kext in kext_list:
            hv = self.check_update(kext)
            if hv:
                kext["last_notified"] = hv
                ups.append(kext)
        return ups

    def check_update(self, kext_dict):
        # Checks the passed kext_dict to see if there's an update
        # Structure is like:
        # { "name" : "kextname", "url" : "kexturl", "last_built" : "buildhash", "last_notified" : "notifyhash" }
        hash_val = self.get_hash(kext_dict["url"])
        if hash_val and hash_val.lower() not in [kext_dict.get("last_built", "").lower(), kext_dict.get("last_notified", "").lower()]:
                return hash_val
        return None

if __name__ == "__main__":
    # Launch the script
    k = KextUpdater()
    try:
        k.start()
    except Exception as e:
        k.re.notify("Error!", str(e))