# Ubuntu-patch-verification
This is the source code and setup/running steps that were used for the CS 6348 final project: "Using Gray-Box Fuzzing to Confirm Bug Fixes Between Linux Versions" (Ubuntu 20.04 vs Ubuntu 22.04)

# Docker and AFL fuzzing Set up Steps
**These steps were done in the WSL terminal (Ubuntu) for performance and compatability sake**
## Docker and afl++ network and container setup
- This will put the afl and ubuntu containers on the same local network so that later on afl can communicate with them when doing the fuzzing
1. Pull the docker 22.04 image from the docker desktop
	1. This can also be done through the command line, but its easier visually for me atleast from the desktop (you will have to scroll down to find the exact version)
2. In the WSL terminal run the command (the ubuntu 20.04 is not part of the latest versions so docker desktop wont show it):
	1. docker pull ubuntu:20.04
	2. Check in docker desktop to make sure the 20.04 ubuntu version is there
3. docker pull aflplusplus/aflplusplus

### Network setup
1. ```docker network create fuzz-net```
2. ```docker run -dit --network fuzz-net --name ubuntu2004 ubuntu:20.04```
3. ```docker run -dit --network fuzz-net --name ubuntu2204 ubuntu:22.04```
4. ```docker run -dit --network fuzz-net --name aflplusplus aflplusplus/aflplusplus```

### Verifying connection
1. ```docker exec -it aflplusplus bash```
	1. Will run the aflplusplus bash terminal
2. ```apt-get update && apt-get install -y iputils-ping```
	1. Installs the linux ping feature which sends network packets to a machine to see if its alive
	2. If you see ?bytes from ubuntu then that means your able to communicate
3. ```ping ubuntu2004```
4. ```ping ubuntu2204```

## Setting up the environment
- Remove the old container that were used for network testing:
```
docker rm ubuntu2004
docker rm ubuntu2204
docker rm aflplusplus
```
- Make this project structure:
```
mkdir -p ~/fuzzing-project/seeds/grep
mkdir -p ~/fuzzing-project/seeds/tar
mkdir -p ~/fuzzing-project/seeds/objdump
mkdir -p ~/fuzzing-project/scripts
mkdir -p ~/fuzzing-project/output
```
- Remake the containers: (This will connect AFL++ containter to the network and mount a volume)
```
docker run -dit --network fuzz-net --name ubuntu2004 ubuntu:20.04

docker run -dit --network fuzz-net --name ubuntu2204 ubuntu:22.04

docker run -dit --network fuzz-net --name aflplusplus -v ~/fuzzing-project:/fuzzing aflplusplus/aflplusplus
```
- Verify everything looks good:
```
docker network inspect fuzz-net
```

### Installs (for the 2 ubuntu containers)
- ```apt-get update``` (for both ubuntu containers)
	- Each ubuntu version will have its own cli tool versions especially with ubuntu 20.04 having older versions
	- *This will allow testing grep and tar cli tools*
- ```apt-get update && apt-get install -y binutils```
	- *Allows testing the bintutils*

## Making the seed inputs
Run the afl++ container **through you wsl terminal**
	1. Command: ```docker exec -it aflplusplus bash```

### Grep
- Make the seed files, copy the values provided in the seeds/grep directory in the github, and paste them into the respective seed file in the terminal
- *Verify that the files are on your host machine by checking the folders and the following contents in the files*
### tar
1. Go to the tmp folder in the terminal
2. Make 2 files with random contents, ex: testfile.txt, contents: "hello there"
3. Run this tar command to make a tar file seed:
	1. ```tar -cf /fuzzing/seeds/tar/seed1.tar /tmp/testfile.txt```
4. To verify it worked use this command and see if there is size amount:
	1. ```tar -tvf /fuzzing/seeds/tar/seed1.tar```
5. This will simulate having a tar file containing 2 files:
	1. ```tar -cf /fuzzing/seeds/tar/seed2.tar /tmp/testfile.txt /tmp/testfile2.txt```
6. A seed with a more compressed tar file:
	1. ```tar -czf /fuzzing/seeds/tar/seed3.tar.gz /tmp/testfile.txt```
### objdump
- For objdump in binutils, you can copy the binary files from ubuntu bin folder which houses binary files for commands
1. ```cp /bin/ls /fuzzing/seeds/objdump/seed1.elf```
2. ```cp /bin/cp /fuzzing/seeds/objdump/seed2.elf```
3. ```cp /bin/cat /fuzzing/seeds/objdump/seed3.elf```
4. Verify: ```ls -la /fuzzing/seeds/objdump/```

## Wrapper scripts
- These scripts are used to help automate the process of taking the input and running the actual command using them
- They are shell scripts that can be found in: *scripts* folder
  - Copy each shell script, make those files in the scripts folder in the terminal, and paste those copied scripts to the respective files
- **Make sure to give them execution permissions**:

## Testing if QEMU works
- This will be checked in the afl++ container
- Checks is QEMU is there: ```ls /AFLplusplus/ | grep qemu```
- Tests a sample:
	- ```afl-fuzz -Q -i /fuzzing/seeds/objdump -o /fuzzing/output/objdump_test -- objdump -d @@```

# Running AFL++ and the Harness
## AFL
1. In the harness at this line : ``` LOG_PATH = Path("/home/YOURPATH/fuzzing-project/output/divergences.jsonl") ``` change the path ("YOURPATH") to point to divergences.jsonl based on your setup path
2. ```docker start ubuntu2004 ubuntu2204 aflplusplus```
3. ```docker exec -it aflplusplus bash```
4. ```tmux new-session -s NAMEOFSESSION``` (change the NAMEOFSESSION to tmux session name)
5. ```Commands to run AFL++ for each CLI tool```
	- Grep Command: ```afl-fuzz -Q -i /fuzzing/seeds/grep -o /fuzzing/output/grep_results -- grep -E -f @@```
 	- Objdump Command: ```afl-fuzz -Q -i /fuzzing/seeds/objdump -o /fuzzing/output/objdump_results -- objdump -d @@ ```
	- Tar Command: ```afl-fuzz -Q -i /fuzzing/seeds/tar -o /fuzzing/output/tar_results -- tar -tvf @@```
7. Detach from the tmux session
## Harness
1. Change the permission of the results folder based on which CLI tool is being tested (to allow harness to read it): ```sudo chmod -R 755 ~/fuzzing-project/output/CLITOOL_results``` (change the "CLITOOL" to either grep, objdump, or tar)
2. ```tmux new-session -s harness```
3. ```python3 ~/fuzzing-project/harness.py watch CLITOOL``` (change the "CLITOOL" to either grep, objdump, or tar)

**The results to look for are the divergences.jsonl, crashs/hangs in the outputs directory**
