import sys
import os
import time
import json
import KextBuilder
import tempfile

# Don't edit the following line - it handles self-updating:

# version 0.0.1

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

        self.plugs = json.load(open("plugins.json"))["Plugins"]

    # Helper methods
    def grab(self, prompt):
        if sys.version_info >= (3, 0):
            return input(prompt)
        else:
            return str(raw_input(prompt))

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

    def check_update(self):
        # Checks against https://github.com/corpnewt/Lilu-and-Friends to see if we need to update
        return
        

    def main(self):
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
