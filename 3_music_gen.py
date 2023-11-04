# !/usr/bin/env python3

import yaml  # pip install PyYAML

import os
import time
import json
import subprocess
import utils
import shutil
import random
from pathlib import Path



# video file we wish to render
path_base = os.path.dirname(os.path.abspath(__file__))
# video_file = path_base + "/config/ambient_videos.yaml"
# config_file = path_base + "/config/ambient_youtube_video.yaml"


path_twitch_ffmpeg = path_base + "/thirdparty/ffmpeg-N-99900-g89429cf2f2-win64-lgpl/ffmpeg.exe"
path_twitch_ffprob = path_base + "/thirdparty/ffmpeg-N-99900-g89429cf2f2-win64-lgpl/ffprobe.exe"

path_output = path_base + "/song_export/"

# now lets generate a valid set of segments
number_of_segments = 4
segment_length = 25 * 60


#========================================================================================
#========================================================================================
#========================================================================================


# Here we will read in all songs from disk and get their length
filenames = []
files = []
lengths = []
total_playtime = 0
for filename in os.listdir(os.path.join(path_base, "songs")):
    # add how long this clip is
    # https://superuser.com/a/945604
    file = os.path.join(path_base, "songs", filename)
    cmd = path_twitch_ffprob \
          + " -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 " \
          + "\"" + file + "\""
    pipe = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    vid_length = pipe.communicate()[0]
    filename_clean = Path(filename).stem
    # print(f"{filename_clean} => {float(vid_length)} seconds")
    # save to our list!
    files.append(file)
    filenames.append(filename_clean)
    lengths.append(float(vid_length))
    total_playtime = total_playtime + float(vid_length)

# nice summary
print(f"loaded a total of {len(files)} songs from file...")
print(f"total playtime is {total_playtime/3600:3.2f} hours..")
print()


# we will try to generate a segment list of songs that fit in the requested length
indexes = list(range(0,len(files)))
random.shuffle(indexes)
segments = []
for r in range(0, number_of_segments):
    time_total = 0
    segment = []
    failure = False 
    while len(indexes) > 0 and not failure:
        # find a valid segment that fits in our segment length
        found = False
        for i in range(0,len(indexes)):
            index = indexes[i]
            if time_total + lengths[index] >= segment_length:
                continue
            time_total = time_total + lengths[index]
            segment.append(index)
            found = True
            del indexes[i]
            break
        # if we didn't find a valid song, then we are done with this segment
        if not found:
            failure = True

    # done!
    print(f"segment {r} had {time_total/60.0:3.2f} of {segment_length/60.0:3.2f}")
    print(f"  -> used a total of {len(segment)} songs ({len(indexes)} remain)")

    # record the last added segment and its length
    index_last_segment = segment[-1]
    time_last_segment = lengths[index_last_segment]
    time_total = time_total - time_last_segment

    # try to see if there is a song that will bring us to a closer time than the last one
    # e.g. we greedly added songs that were not past the max length allowed, so we could have
    # a multiple minute gap at the end of the segment, which we hope to avoid here
    min_dt_pos = -1
    min_dt_index = index_last_segment
    min_dt = (segment_length - time_total - time_last_segment)
    for i in range(0,len(indexes)):
        index = indexes[i]
        if time_total + lengths[index] >= segment_length:
            continue
        dt = (segment_length - time_total - lengths[index])
        if dt < min_dt:
            min_dt_pos = i
            min_dt_index = index
            min_dt = dt
    
    # if we found one that minimized the difference, then lets append it
    # we will remove the old index and then append this new one
    if min_dt_pos != -1:
        print(f"  -> switching last segment (brings {(time_total+lengths[index_last_segment])/60:3.2f} to {(time_total+lengths[min_dt_index])/60:3.2f} min)")
        del segment[-1]
        segment.append(min_dt_index)
        time_total = time_total + lengths[min_dt_index]
        del indexes[min_dt_pos]
        indexes.append(index_last_segment)
    segments.append(segment)

# nice printout to the user
print()
for r in range(0,len(segments)):
    print(f"segment {r} ======")
    segment = segments[r]
    time_total = 0
    for index in segment:
        time_total = time_total + lengths[index]
        print(f"  {time_total/60.0:3.2f} -> {filenames[index]} ({lengths[index]/60.0:3.2f} length)")



#========================================================================================
#========================================================================================
#========================================================================================


# clear old results
if os.path.exists(path_output):
    shutil.rmtree(path_output)
os.makedirs(path_output)


# copy in each folder
for r in range(0,len(segments)):
    savepath = os.path.join(path_output, f"segment_{r:02d}")
    os.makedirs(savepath)
    for index in segment:
        fileout = os.path.join(savepath, Path(files[index]).name)
        shutil.copy(files[index], fileout)

