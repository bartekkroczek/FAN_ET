#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os.path import join
import yaml
from psychopy import visual, core, logging, event, gui
from psychopy.iohub import ioHubExperimentRuntime, module_directory, getCurrentDateTimeString
import csv
import codecs
from misc.screen import get_screen_res
import atexit
from problemGenerator.concrete_experiment import concrete_experiment

STIMULI_PATH = join('.', 'stimuli', 'all')
VISUAL_OFFSET = 150
TEXT_SIZE = 30
SCALE = 0.65
TRIGGER_LIST = []
RESULTS = [['session_id', 'start_time', 'end_time', 'choosed_option', 'ans_accept', 'rt', 'corr', 'time', 'rel', 'feedb', 'wait', 'exp', 'type']]
PART_ID = ''


# TIME, REL, FEEDB, WAIT, EXP, POS  (pozycja z sześciu, na której była prezentowana opcja D),
#  LATENCY (czas odpowiedzi – naciśnięcia „zatwierdź
# odpowiedź”), OPT1 (0 albo 1 gdy wybrano opcję 1), OPT2 (0 albo 1 gdy wybrano opcję 2), OPT3 (0 albo 1 gdy wybrano
# opcję 3), OPT4 (0 lub 1 albo wybrano opcję 4), OPT5 (0 albo 1 gdy wybrano opcję 5), OPT6 (0 albo 1 gdy wybrano opcję
# 6), NORESP (0 albo 1 gdy nie wybrano żadnej opcji), TOTAL (liczba cech zmienionych w opcji D), SIMILARITY (0..1).

# 'time', 'rel', 'feedb', 'wait', 'exp', 'type'
@atexit.register
def save_beh_results():
    global PART_ID
    with open(join('results', PART_ID + '_beh.csv'), 'w') as beh_file:
        beh_writer = csv.writer(beh_file)
        beh_writer.writerows(RESULTS)
    logging.flush()
    with open(join('results', PART_ID + '_triggermap.txt'), 'w') as trigger_file:
        trigger_writer = csv.writer(trigger_file)
        trigger_writer.writerows(TRIGGER_LIST)


def read_text_from_file(file_name, insert=''):
    """
    Method that read message from text file, and optionally add some
    dynamically generated info.
    :param file_name: Name of file to read
    :param insert:
    :return: message
    """
    if not isinstance(file_name, str):
        logging.error('Problem with file reading, filename must be a string')
        raise TypeError('file_name must be a string')
    msg = list()
    with codecs.open(file_name, encoding='utf-8', mode='r') as data_file:
        for line in data_file:
            if not line.startswith('#'):  # if not commented line
                if line.startswith('<--insert-->'):
                    if insert:
                        msg.append(insert)
                else:
                    msg.append(line)
    return ''.join(msg)


def check_exit(key='f7'):
    stop = event.getKeys(keyList=[key])
    if len(stop) > 0:
        logging.critical('Experiment finished by user! {} pressed.'.format(key))
        exit(1)


def show_info(win, file_name, insert=''):
    """
    Clear way to show info message into screen.
    :param win:
    :return:
    """
    msg = read_text_from_file(file_name, insert=insert)
    msg = visual.TextStim(win, color='black', text=msg, height=TEXT_SIZE - 5, wrapWidth=SCREEN_RES['width'])
    msg.draw()
    win.flip()
    key = event.waitKeys(keyList=['f7', 'return', 'space'])
    if key == ['f7']:
        abort_with_error('Experiment finished by user on info screen! F7 pressed.')
    flip_time = win.flip()
    return flip_time


def abort_with_error(err):
    logging.critical(err)
    raise Exception(err)


class StimulusCanvas(object):
    def __init__(self, win, figs_desc, scale=1.0, frame_color=u'crimson', pos=None):
        self._figures = list()
        self._frame = visual.Rect(win, width=375 * scale, height=375 * scale, lineColor=frame_color, lineWidth=5)
        inner_shift = 90 * scale
        shifts = [(-inner_shift, inner_shift), (inner_shift, inner_shift), (-inner_shift, -inner_shift),
                  (inner_shift, -inner_shift)]
        for fig_desc, inner_shift in zip(figs_desc, shifts):
            fig = "{figure}_{brightness}_{frame}_{rotation}.png".format(**fig_desc)
            fig = join(STIMULI_PATH, fig)
            fig = visual.ImageStim(win, fig, interpolate=True)
            fig.size = fig.size[0] * scale, fig.size[1] * scale
            fig.pos += inner_shift
            self._figures.append(fig)
        if pos:
            self.setPos(pos)

    def setFrameColor(self, color):
        self._frame.setLineColor(color)

    def setAutoDraw(self, draw):
        self._frame.setAutoDraw(draw)
        [x.setAutoDraw(draw) for x in self._figures]

    def draw(self):
        self._frame.draw()
        [x.draw() for x in self._figures]

    def setPos(self, pos):
        self._frame.pos += pos
        for fig in self._figures:
            fig.pos += pos


class ExperimentRuntime(ioHubExperimentRuntime):
    def run(self, *args):
        global PART_ID
        info = {'Part_id': '', 'Part_age': '20', 'Part_sex': ['MALE', "FEMALE"],
                'ExpDate': '06.2016'}
        dictDlg = gui.DlgFromDict(dictionary=info, title='FAN', fixed=['ExpDate'])
        if not dictDlg.OK:
            exit(1)
        try:
            tracker = self.hub.devices.tracker
        except Exception:
            # No eye tracker config found in iohub_config.yaml
            from psychopy.iohub.util import MessageDialog
            md = MessageDialog(title="No Eye Tracker Configuration Found",
                               msg="Update the iohub_config.yaml file by "
                                   "uncommenting\nthe appropriate eye tracker "
                                   "config lines.\n\nPress OK to exit demo.",
                               showButtons=MessageDialog.OK_BUTTON,
                               dialogType=MessageDialog.ERROR_DIALOG,
                               allowCancel=False,
                               display_index=0)
            md.show()
            return 1

        display = self.hub.devices.display

        PART_ID = str(info['Part_id'] + info['Part_sex'] + info['Part_age'])
        logging.LogFile(join('results', PART_ID + '.log'), level=logging.INFO)

        concrete_experiment(join('problemGenerator', 'experiment.csv'), info['Part_id'], info['Part_sex'],
                            info['Part_age'])
        data = yaml.load(open(join('results', PART_ID + '.yaml'), 'r'))
        SCREEN_RES = get_screen_res()
        tracker.runSetupProcedure()

        res = display.getPixelResolution()  # Current pixel resolution of the Display to be used
        coord_type = display.getCoordinateType()
        window = visual.Window(res, monitor=display.getPsychopyMonitorName(), units=coord_type, fullscr=True,
                               allowGUI=False, screen=display.getIndex(), color='Gainsboro')

        to_label = visual.TextStim(window, text=u'To:', color=u'black', height=50, pos=(
            -SCREEN_RES['width'] / 2.0 + VISUAL_OFFSET, SCREEN_RES['height'] / 1.96 - SCREEN_RES['height'] / 3.0))
        is_like_label = visual.TextStim(window, text=u'Is Like:', color=u'black', height=50, pos=(
            -SCREEN_RES['width'] / 2.0 + VISUAL_OFFSET, SCREEN_RES['height'] / 2.02 - 2 * SCREEN_RES['height'] / 3.0))
        line = visual.Line(window, start=(-SCREEN_RES['width'] / 3.8, -550), end=(-SCREEN_RES['width'] / 3.8, 550),
                           lineColor=u'black', lineWidth=10)
        to_choose_one_label = visual.TextStim(window, text=u'To: (Choose one)', color=u'black', height=50,
                                              wrapWidth=1500,
                                              pos=(50, 2.7 * SCREEN_RES['height'] / 7.0))
        time_left_label = visual.TextStim(window, text=u'16 seconds left.', height=50, color=u'black',
                                          wrapWidth=1000,
                                          pos=(-1.5 * SCREEN_RES['width'] / 13.0, -3 * SCREEN_RES['height'] / 7.0))
        accept_box = visual.Rect(window, fillColor=u'dimgray', width=600, height=100,
                                 pos=(4.6 * SCREEN_RES['width'] / 13.0, -3 * SCREEN_RES['height'] / 7.0 - 40),
                                 lineColor=u'black')
        accept_label = visual.TextStim(window, text=u'Accept answer', height=50, color=u'ghostwhite', wrapWidth=900,
                                       pos=(
                                           4.6 * SCREEN_RES['width'] / 13.0, -2.8 * SCREEN_RES['height'] / 7.0 - 60))
        LABELS = [to_label, is_like_label, line, to_choose_one_label, time_left_label, accept_box, accept_label]
        end_of_instruction = True
        flip_time = None
        for t, block in enumerate(data['list_of_blocks']):
            # TODO: ADD break support
            for trial in block['experiment_elements']:
                if trial['type'] == 'instruction':
                    flip_time = show_info(window, join('.', 'messages', trial['path']))
                    continue
                if end_of_instruction:
                    end_of_instruction = False
                    self.hub.sendMessageEvent(text="EXPERIMENT_START", sec_time=flip_time)
                    self.hub.sendMessageEvent(text="IO_HUB EXPERIMENT_INFO START")
                    self.hub.sendMessageEvent(text="ioHub Experiment started {0}".format(getCurrentDateTimeString()))
                    self.hub.sendMessageEvent(text="Experiment ID: {0}, Session ID: {1}".format(self.hub.experimentID,
                                                                                                self.hub.experimentSessionID))
                    self.hub.sendMessageEvent(
                        text="Stimulus Screen ID: {0}, Size (pixels): {1}, CoordType: {2}".format(display.getIndex(),
                                                                                                  display.getPixelResolution(),
                                                                                                  display.getCoordinateType()))
                    self.hub.sendMessageEvent(
                        text="Calculated Pixels Per Degree: {0} x, {1} y".format(*display.getPixelsPerDegree()))
                    self.hub.sendMessageEvent(text="IO_HUB EXPERIMENT_INFO END")
                    self.hub.clearEvents('all')

                [lab.setAutoDraw(True) for lab in LABELS]
                A = StimulusCanvas(win=window, figs_desc=trial['matrix_info'][0]['parameters'], scale=SCALE,
                                   frame_color=u'black', pos=(
                        -SCREEN_RES['width'] / 2.0 + VISUAL_OFFSET, SCREEN_RES['height'] / 2.0 - VISUAL_OFFSET))
                B = StimulusCanvas(win=window, figs_desc=trial['matrix_info'][1]['parameters'], scale=SCALE,
                                   frame_color=u'black', pos=(-SCREEN_RES['width'] / 2.0 + VISUAL_OFFSET,
                                                              SCREEN_RES['height'] / 2.05 - VISUAL_OFFSET - SCREEN_RES[
                                                                  'height'] / 3.0))
                C = StimulusCanvas(win=window, figs_desc=trial['matrix_info'][2]['parameters'], scale=SCALE,
                                   frame_color=u'black', pos=(-SCREEN_RES['width'] / 2.0 + VISUAL_OFFSET,
                                                              SCREEN_RES['height'] / 2.1 - VISUAL_OFFSET - 2 *
                                                              SCREEN_RES[
                                                                  'height'] / 3.0))
                figures = [A, B, C]
                solutions = [
                    StimulusCanvas(window, trial['matrix_info'][i]['parameters'], scale=SCALE, frame_color=u'dimgray')
                    for i
                    in range(3, 9)]
                [solution.setPos((150, 0)) for solution in solutions]

                shifts = [(-SCREEN_RES['width'] / 4.0, SCREEN_RES['height'] / 6.0), (0, SCREEN_RES['height'] / 6.0),
                          (SCREEN_RES['width'] / 4.0, SCREEN_RES['height'] / 6.0),
                          (-SCREEN_RES['width'] / 4.0, -SCREEN_RES['height'] / 6.0), (0, -SCREEN_RES['height'] / 6.0),
                          (SCREEN_RES['width'] / 4.0, -SCREEN_RES['height'] / 6.0)]
                for solution, shift in zip(solutions, shifts):
                    solution.setPos(shift)
                figures.extend(solutions)
                timer = core.CountdownTimer(trial['time'])
                [fig.setAutoDraw(True) for fig in figures]
                mouse = event.Mouse()
                choosed_option = -1
                ans_accept = False
                rt = -1
                # self.hub.sendMessageEvent(text="EXPERIMENT_START", sec_time=flip_time)
                trial_start = True
                stime = None
                while timer.getTime() > 0.0 and not ans_accept:
                    for idx, sol in enumerate(solutions, 3):
                        if mouse.isPressedIn(accept_box) and choosed_option != -1:
                            ans_accept = True
                            rt = trial['time'] - timer.getTime()
                            break
                        if mouse.isPressedIn(sol._frame):
                            sol.setFrameColor('green')
                            choosed_option = idx
                        if choosed_option != idx:
                            if sol._frame.contains(mouse):
                                sol.setFrameColor('yellow')
                            else:
                                sol.setFrameColor('gray')
                    time_left_label.setText(u'{} seconds left.'.format(int(timer.getTime())))
                    flip_time = window.flip()
                    if trial_start:
                        trial_start = False
                        self.hub.sendMessageEvent(text="TRIAL_START", sec_time=flip_time)
                        stime = flip_time
                        tracker.setRecordingState(True)
                    gpos = tracker.getPosition()
                    if type(gpos) in [tuple, list]:
                        self.hub.sendMessageEvent("IMAGE_UPDATE %.3f %.3f" % (gpos[0], gpos[1]), sec_time=flip_time)
                    else:
                        self.hub.sendMessageEvent("IMAGE_UPDATE [NO GAZE]", sec_time=flip_time)
                    check_exit()
                if choosed_option != -1:
                    choosed_option = trial['matrix_info'][choosed_option]['name']
                corr = choosed_option == 'D1'
                [fig.setAutoDraw(False) for fig in figures]
                [lab.setAutoDraw(False) for lab in LABELS]
                flip_time = window.flip()
                etime = flip_time
                self.hub.sendMessageEvent(text="TRIAL_END %d" % t, sec_time=flip_time)
                tracker.setRecordingState(False)
                self.hub.clearEvents('all')
                RESULTS.append([self.hub.getSessionID(), stime, etime, choosed_option, ans_accept, rt, corr, trial['time'], trial['rel'], trial['feedb'],
                                trial['wait'], trial['exp'], trial['type']])
        flip_time = window.flip()
        self.hub.sendMessageEvent(text='EXPERIMENT_COMPLETE', sec_time=flip_time)
        tracker.setConnectionState(False)
        save_beh_results()
        logging.flush()
        flip_time = show_info(window, join('.', 'messages', 'end.txt'))
        self.hub.sendMessageEvent(text="SHOW_DONE_TEXT", sec_time=flip_time)
        self.hub.clearEvents('all')
        window.close()


if __name__ == '__main__':
    runtime = ExperimentRuntime(module_directory(ExperimentRuntime.run), "experiment_config.yaml")
    runtime.start()
