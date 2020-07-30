from music21 import converter, corpus, instrument, midi, note, tempo
from music21 import chord, pitch, environment, stream, analysis, duration
import glob
import numpy as np
from tqdm import tqdm
import os
import pandas as pd
import random
from config import get_config


random.seed(123)
##for visualize
# pd.set_option('display.max_rows', None)
# pd.set_option('display.max_columns', None)
# pd.set_option('display.width', None)
# pd.set_option('display.max_colwidth', None)

class Generator:
    def __init__(self, args):
        self.config = args
        self.song_dict = dict()

    def run(self):

        dataset_dir = self.config.midi_files_path
        input_path = self.config.input_save_path
        data_list, composers = self.get_data_list(dataset_dir + 'maestro-v2.0.0_cleaned.csv')

        for i,(composer, num) in tqdm(enumerate(composers.items())): #enumerate over composers
            if i==0: continue #TODO: just for test REMOVE!
            count_file = 0  # count files for each composer

            print("################################## {} ####################################".format(composer))

            for data in data_list:
                track_comp, orig_name, file_name = data[0], data[1], data[2]

                if track_comp is composer:
                    version = self.fetch_version(orig_name)
                    print(self.song_dict)
                    fsave_dir = input_path + 'Composer'+ str(i) + '/' + orig_name  #dir to save segments
                    try:
                        mid = self.open_midi(dataset_dir + data[2])

                    except:
                        print("ERROR: failed to open {}\tSKIPPING...".format(file_name))

                    else:
                        segments = self.generate_segments(mid)  # list of segments
                        if segments == -1:  # TODO: reformat as error
                            print("ERROR: failed to segment {}\tSKIPPING...".format(file_name))
                            continue
                        self.save_input(segments, fsave_dir, version)
                        count_file += 1
                        print("{} success: {} -> {}".format(count_file, file_name, orig_name))

        return

    def get_data_list(self, fdir): #return preprocessed list of paths
        data = pd.read_csv(fdir) #cleaned csv
        data = data.drop(['split', 'year', 'audio_filename', 'duration'], axis=1) #drop unnecessary columns

        data_list = list(zip(data['canonical_composer'], data['canonical_title'], data['midi_filename']))
        composers = dict(data['canonical_composer'].value_counts())

        return data_list, composers

    def fetch_version(self, track):
        version = 0
        if track in self.song_dict:
            version = self.song_dict[track]
            self.song_dict[track] = version + 1 #update
        else:
            self.song_dict.update({track : 0})

        return version

    def open_midi(self, file):
        mf = midi.MidiFile()
        mf.open(file)
        mf.read()
        mf.close()
        return midi.translate.midiFileToStream(mf)

    def save_input(self, matrices, save_dir, vn):
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        for i, mat in enumerate(matrices):
            np.save(save_dir + "/ver" + str(vn) + '_seg' + str(i), mat)  # save as .npy
        return

    def generate_segments(self, mid): #mid = each track(song)

        stm_instr = instrument.partitionByInstrument(mid)
        if stm_instr == None: # 1. no tracks in stream
            print("SKIP: No tracks found...")
            return -1

        generated_input = []
        for pt in stm_instr:  # each part(instrument) -> piano
            instr_index = pt.getInstrument().midiProgram

            if instr_index != 0: # 2. not piano track
                return -1

            on, off, dur, pitch, vel = self.extract_notes(pt)  # send track -> get lists of info
            if len(on) < 1:  # 3. no notes in this track
                return -1

            ##segmentation
            #10 segments each song -> 200 seconds
            track_dur = off[len(off) - 1]
            track_seg = int(track_dur / 20)
            seg_length = 400 # 20 seconds

            if track_seg < 10: # not used
                return -1
            elif track_seg >= 10:
                rnd_selected = random.sample(range(track_seg),10) #randomly select 10 segments
                rnd_selected.sort()
                for i in rnd_selected:
                    segment = [
                        [[0 for k in range(128)] for i in range(seg_length)] for j in range(2)
                    ]

                    start, end = i*20, (i+1)*20
                    for j, note in enumerate(zip(on, off, dur, pitch, vel)): #zip lists

                        x_index = int((note[0] - start) / 0.05)  # time
                        y_index = int(note[3])  # pitch

                        #note
                        # if note[0] > end and note[1] < start: continue
                        if (note[0] >= start and note[0] < end) or (note[1] > start and note[1] <= end):
                            for t in range(int(note[2] / 0.05)):  # mark all cells in duration
                                if (x_index + t) >= 400: break
                                segment[1][x_index + t][y_index] = int(note[4])
                        #onset
                        if note[0] >= start and note[0] < end:
                            segment[0][x_index][y_index] = 1


                    generated_input.append(segment)

        return generated_input #list of matrices

    def extract_notes(self, track):
        offset_list = track.secondsMap
        on, off, dur, pitch, vel = [], [], [], [], []
        for evt in offset_list:
            element = evt['element']
            if type(element) is note.Note:
                on.append(evt['offsetSeconds'])
                off.append(evt['endTimeSeconds'])
                dur.append(evt['durationSeconds'])
                pitch.append(element.pitch.ps)
                vel.append(element.volume.velocity)
            elif type(element) is chord.Chord:
                for nt in element.notes:
                    on.append(evt['offsetSeconds'])
                    off.append(evt['endTimeSeconds'])
                    dur.append(evt['durationSeconds'])
                    pitch.append(nt.pitch.ps)
                    vel.append(nt.volume.velocity)

        return on, off, dur, pitch, vel


########################################
# Testing
config, unparsed = get_config()
# for arg in vars(config):
#     argname = arg
#     contents = str(getattr(config, arg))
    # print(argname + " = " + contents)
temp = Generator(config)
temp.run()
