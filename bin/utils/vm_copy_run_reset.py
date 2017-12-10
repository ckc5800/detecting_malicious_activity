import argparse
import configparser
import datetime
import os
import random
import string

from time import sleep
from lib.vmrun import vmrun


class Runner:
    
    def __init__(self, conf, args):
        self.conf = conf
        self.args = args
        self.vm = vmrun(
            vmx = self.conf.get("vm", "vmx"),
            user = self.conf.get("vm", "user"),
            password = self.conf.get("vm", "password")
        )

        self.run()

    def run(self):

        time = datetime.datetime.utcnow()
        time_str = str(time).replace("-", "_").replace(" ", "_").replace(":", "_").split(".")[0]
        out_dir = self.args.log_dir + "/" + time_str

        os.makedirs(out_dir)

        print(f"[*] Created log folder at {out_dir}")

        for time in range(self.args.times):
            
            print(f"[*] Starting run {time+1}")

            self.reset_to_snapshot()

            print(f"[*] Copying over files to {self.args.dest_path}")
            

            for file in os.listdir(self.args.path):
                src_path = self.args.path + '/' + file
                
                # If its our executable, rename depending on mode parameter.
                if file[-4:] == '.exe':
                    if self.args.normal:
                        file_to_run = dst_path = self.args.dest_path + '\\' + self.args.normal
                    else:
                        file_to_run = dst_path = self.args.dest_path + '\\' + self.random_string()
                    
                    print(f"[*] Renamed {file} to {file_to_run}")

                else:
                    dst_path = self.args.dest_path + '\\' + file
                

                assert(self.vm.copyFileFromHostToGuest(src_path, f"\"{dst_path}\"") == [])

            print(f"[*] Moved over all files to {self.args.dest_path}")

            print(f"[*] Executing {file_to_run}")
            
            assert(self.vm.runProgramInGuest(f"\"{file_to_run}\"", "i") == [])

            print(f"[*] Succesfully ran {file_to_run}")

            print("[*] Sleeping 30 seconds to allow for execution")

            sleep(30)

            print(f"[*] Grabbing Sysmon logs for run #{time+1}")

            dst_log = out_dir + "/sysmon_log_" + str(time+1)
            assert(self.vm.copyFileFromGuestToHost(
                "\"C:\\Windows\\System32\\winevt\\Logs\\Microsoft-Windows-Sysmon%4Operational.evtx\"",
                dst_log
            ) == [])

            print(f"[*] Copied over this runs sysmon logs to {dst_log}")
            print(f"[*] Finished run {time+1}")
        
        print("[*] Finished log collection, exiting..")

    
    def random_string(self):
        return (''.join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits
        ) for _ in range(random.randint(8,24)))) + ".exe"
            

    def reset_to_snapshot(self):
        print("[*] Reverting To Base Snapshot...")
    
        base_snap = self.conf.get("vm", "snapshot")
    
        assert(self.vm.revertToSnapshot(base_snap) == [])
    
        print("[*] Reverted VM To " + base_snap)

        print("[*] Starting VM After Snapshot")
        assert(self.vm.start() == [])
        print("[*] Started VM")
    

def main():
    
    args = create_parser()
    conf = configparser.ConfigParser()

    conf.read("config.ini")

    Runner(conf, args)
    



def create_parser():
    
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", help="The folder containing the files to copy over. This script executes the first .exe it finds in this folder on the VM")
    parser.add_argument("--log_dir", help="The directory to put the sysmon logs copied over after." \
                                        "the log files will be placed in $log_dir/<time>/")
    parser.add_argument("--times", help="Number of times to run the executable (default 1)", default=1,
                        type=int)
    parser.add_argument("--dest_path")
    mode = parser.add_mutually_exclusive_group(required=True)

    normal = mode.add_argument(
        "--normal",
        help="Run the executable with the provided name"
    )

    randomize = mode.add_argument(
        "--randomize",
        help="Run the executable --times <n> times with a randomly generated name each time" \
                    "and copy over the sysmon log after each run",
        action="store_true"
    )




    return parser.parse_args()


if __name__ == "__main__":
    main()