# !/usr/bin/env python3

import yaml  # pip install PyYAML

import os
import time
import json
import subprocess
import utils
import shutil

# video file we wish to render
path_base = os.path.dirname(os.path.abspath(__file__))
video_file = path_base + "/config/ambient_videos.yaml"
config_file = path_base + "/config/ambient_youtube_video.yaml"

# paths of the cli and data
# path_twitch_ffmpeg = path_base + "/thirdparty/ffmpeg-4.3.1-amd64-static/ffmpeg"
# path_twitch_ffprob = path_base + "/thirdparty/ffmpeg-4.3.1-amd64-static/ffprobe"
path_twitch_ffmpeg = path_base + "/thirdparty/ffmpeg-N-99900-g89429cf2f2-win64-lgpl/ffmpeg.exe"
path_twitch_ffprob = path_base + "/thirdparty/ffmpeg-N-99900-g89429cf2f2-win64-lgpl/ffprobe.exe"
path_font = path_base.replace("\\", "/").replace(":", "\\\\:") + "/thirdparty/font_balgruf/BalgrufItalic-GOyem.ttf"
path_root = path_base + "/"
path_render = path_base + "/data_rendered/"
# path_temp = "/tmp/tvc_render_segments/"
path_temp = path_base + "/data_temporary/"

# ================================================================
# ================================================================

# load the yaml from file
with open(config_file) as f:
    config = yaml.load(f, Loader=yaml.FullLoader)
print("loaded config file: " + config_file)

# load the template file for the description
template_file = path_base + "/config/" + config["yt_template"]
with open(template_file, "r") as myfile:
    template = myfile.read()
print("loaded template file: " + template_file)

# setup control+c handler
utils.setup_signal_handle()

# load the yaml from file
with open(video_file) as f:
    data = yaml.load(f, Loader=yaml.FullLoader)
print("loaded " + str(len(data)) + " videos to render")

# loop through each video and render each segment
# we will want to first ensure chat is rendered
# from there we will render the full segmented video
for video in data:

    # check if we should download any more
    if utils.terminated_requested:
        print('terminate requested, not downloading any more..')
        break

    # nice debug print
    print("processing " + video["video"])

    # VIDEO: check that we have the video
    file_path_video = path_root + video["video"] + ".mp4"
    if not os.path.exists(file_path_video):
        print("\t- ERROR: could not find the video file!")
        print("\t- " + file_path_video)
        continue

    # # INFO: open the data file
    # file_path_info = path_root + video["video"] + "_info.json"
    # # print("\t- opening info: " + file_path_info)
    # with open(file_path_info) as f:
    #     video_info = json.load(f)

    # delete the temp folder if it is there
    clean_video_title = utils.get_valid_filename(video["title"])
    path_temp_parts = path_temp + "/parts/" + clean_video_title + "/"
    if os.path.exists(path_temp_parts) and os.path.isdir(path_temp_parts):
        shutil.rmtree(path_temp_parts)
    if not os.path.exists(path_temp):
        os.makedirs(path_temp)
    if not os.path.exists(path_temp_parts):
        os.makedirs(path_temp_parts)
        
    try:

        # COMPOSITE: render the composite image
        file_path_composite = path_render + video["video"] + "_" + clean_video_title + ".mp4"
        file_path_composite_tmp = path_temp + clean_video_title + ".tmp.mp4"
        if not utils.terminated_requested and not os.path.exists(file_path_composite):

            # now we can render the composite
            print("\t- rendering composite: " + file_path_composite)

            # make directory if needed
            dir_path_composite = os.path.dirname(os.path.abspath(file_path_composite))
            if not os.path.exists(dir_path_composite):
                os.makedirs(dir_path_composite)

            # delete temp file if it is there
            if os.path.exists(file_path_composite_tmp):
                print("\t- deleting temp file: " + file_path_composite_tmp)
                os.remove(file_path_composite_tmp)

            # here we will render each
            seg_start = video["t_start"].split(",")
            seg_end = video["t_end"].split(",")
            dur_segment_total = 0
            t0_big = time.time()
            for idx in range(len(seg_start)):

                # export the segment to a temp folder
                # if we only have a single segment, then no need!
                tmp_output_file = path_temp_parts + "temp_" + str(idx) + ".mp4"
                if len(seg_start) == 1:
                    tmp_output_file = file_path_composite_tmp

                # check if we should download any more
                if utils.terminated_requested:
                    print('terminate requested, not rendering more segments..')
                    break

                # render with chat
                # text fading based on: http://ffmpeg.shanewhite.co/
                # https://superuser.com/a/1296511
                t0 = time.time()
                h1, m1, s1 = seg_start[idx].split(':')
                h2, m2, s2 = seg_end[idx].split(':')
                time1_s = 3600 * int(h1) + 60 * int(m1) + int(s1)
                time2_s = 3600 * int(h2) + 60 * int(m2) + int(s2)
                m, s = divmod(time2_s - time1_s, 60)
                h, m = divmod(m, 60)
                seg_length = format(h, '02') + ':' + format(m, '02') + ':' + format(s, '02')
                cmd = path_twitch_ffmpeg + ' -hide_banner -loglevel quiet -stats ' \
                    + ' -ss ' + seg_start[idx] + ' -i ' + file_path_video + ' -t ' + seg_length \
                    + ' -c:a aac ' \
                    + ' -filter_complex "drawtext=text=\'' + video["title"] \
                    + '\':fontfile=' + path_font + ':fontsize=85:fontcolor=white' \
                    + ':alpha=\'if(lt(t,1),0,if(lt(t,2),(t-1)/1,if(lt(t,28),1,if(lt(t,30),(2-(t-28))/2,0))))\':x=(w-text_w)/2:y=3*(h-text_h)/4"' \
                    + ' -c:v h264_nvenc -avoid_negative_ts make_zero -vsync 2 -map_chapters -1 ' \
                    + tmp_output_file
                # print(cmd)
                subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait()
                # subprocess.Popen(cmd, shell=True).wait()

                # end timing and compute debug stats
                t1 = time.time()
                h1, m1, s1 = seg_start[idx].split(':')
                h2, m2, s2 = seg_end[idx].split(':')
                dur_segment = (int(h2) - int(h1)) * 3600 + (int(m2) - int(m1)) * 60 + (int(s2) - int(s1))
                dur_render = t1 - t0 + 1e-6
                dur_segment_total += dur_segment
                print("\t- time to render: " + str(dur_render))
                print("\t- segment duration: " + str(dur_segment))
                print("\t- realtime factor: " + str(dur_segment / dur_render))

            # If we have multiple segments, then we need to combine them
            # https://stackoverflow.com/a/36045659
            if not utils.terminated_requested and len(seg_start) != 1:
                # text file will all segments
                text_file_temp_videos = path_temp_parts + "videos.txt"
                with open(text_file_temp_videos, 'a') as the_file:
                    for idx in range(len(seg_start)):
                        tmp_output_file = path_temp_parts + "temp_" + str(idx) + ".mp4"
                        the_file.write('file \'' + os.path.abspath(tmp_output_file) + '\'\n')
                # now render
                print("\t- combining all videos into a single segment!")
                cmd = path_twitch_ffmpeg + ' -hide_banner -loglevel quiet -stats ' \
                    + '-f concat -safe 0 ' \
                    + ' -i ' + text_file_temp_videos \
                    + ' -c copy -avoid_negative_ts make_zero -map_chapters -1 ' \
                    + file_path_composite_tmp
                #print(cmd)
                subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait()
                #subprocess.Popen(cmd, shell=True).wait()

                # end timing and compute debug stats
                t1_big = time.time()
                dur_render = t1_big - t0_big + 1e-6
                print("\t- time to render: " + str(dur_render))
                print("\t- segment durations: " + str(dur_segment_total))
                print("\t- realtime factor: " + str(dur_segment_total / dur_render))
            
            # finally copy temp file to new location
            print("\t- renaming temp export file to final filename")
            if not utils.terminated_requested and os.path.exists(file_path_composite_tmp):
                shutil.move(file_path_composite_tmp, file_path_composite)

        # # DESC: description file
        # file_path_desc = path_render + video["video"] + "_" + clean_video_title + "_desc.txt"
        # if not utils.terminated_requested and not os.path.exists(file_path_desc):
        #     print("\t- writting info: " + file_path_desc)
        #     tmp = str(template)
        #     tmp = tmp.replace("$id", video_info["id"])
        #     tmp = tmp.replace("$title", video_info["title"])
        #     # tmp = tmp.replace("$game", video_info["game"])
        #     tmp = tmp.replace("$views", str(video_info["views"]))
        #     tmp = tmp.replace("$t_start", video["t_start"])
        #     tmp = tmp.replace("$t_end", video["t_end"])
        #     tmp = tmp.replace("$recorded", video_info["recorded_at"])
        #     tmp = tmp.replace("$file", video["video"] + ".mp4")
        #     tmp = tmp.replace("$url", video_info["url"])
        #     if "description" in video:
        #         tmp = video["description"] + "\n\n" + tmp
        #     tmp = video["title"] + "\n\n" + tmp
        #     with open(file_path_desc, "w", encoding="utf-8") as text_file:
        #         text_file.write(tmp)



    except Exception as e:
        print("\t- ERROR: " + str(e))

    # clean up our temp parts folder
    if os.path.exists(path_temp_parts) and os.path.isdir(path_temp_parts):
       shutil.rmtree(path_temp_parts)

    # nice split between each segment
    print("")



