from openpyxl import load_workbook
import csv

from classes.experiment import Experiment
from classes.block import Block
from classes.trial import Trial
from classes.parameters import Trial_type, Instruction_type, Per
from classes.instruction import Instruction

__author__ = 'ociepkam'


def load_csv(filemane):
    experiment = []
    number_of_blocks = 0
    with open(filemane, 'rb') as csvfile:
        spamreader = csv.reader(csvfile)
        head = []
        for row_idx, row in enumerate(spamreader):
            if row_idx == 0:
                head = row
            else:
                trial = {}
                for column_idx, column in enumerate(row):
                    if column_idx == 13:
                        break
                    try:
                        trial.update({str(head[column_idx]): int(column)})
                    except:
                        trial.update({str(head[column_idx]): str(column)})
                if trial["BLOCK_NUMBER"] > number_of_blocks and trial["BLOCK_NUMBER"] is not "":
                    number_of_blocks = trial["BLOCK_NUMBER"]
                if trial['BLOCK_NUMBER'] is not "":
                    experiment.append(trial)
    return number_of_blocks, experiment


def load_info(filename):
    experiment_file = load_workbook(filename)
    sheet = experiment_file.get_active_sheet()

    experiment = []
    for row_idx in range(len(sheet.columns[0]) - 1):
        trial = {}
        for column_idx, column in enumerate(sheet.columns):
            if column_idx == 9:
                break
            if isinstance(column[row_idx + 1].value, (str, unicode)):
                trial.update({str(column[0].value): str(column[row_idx + 1].value)})
            elif not isinstance(column[row_idx + 1].value, type(None)):
                trial.update({str(column[0].value): int(column[row_idx + 1].value)})

        experiment.append(trial)

    number_of_blocks = max([int(x.value) for x in sheet.columns[0][1:]])
    return number_of_blocks, experiment


def concrete_experiment(filename, id, sex, age, randomize=True):
    number_of_blocks, data = load_csv(filename)

    experiment = Experiment([], id, sex, age)
    for idx in range(number_of_blocks):
        block = Block([])
        experiment.list_of_blocks.append(block)

    for idx in range(len(data)):
        trial_info = data[idx]
        block_number = trial_info['BLOCK_NUMBER']
        if trial_info['TYPE'] == Trial_type.instruction:
            if trial_info['TIP'][-3:] == 'txt':
                instruction_type = Instruction_type.text
            elif trial_info['TIP'][-3:] == 'bmp' or trial_info['TIP'][-3:] == 'jpg':
                instruction_type = Instruction_type.image
            else:
                raise AssertionError("wrong instruction file type")
            trial = Instruction(trial_info['TIP'], instruction_type, trial_info['SHOW_TIME'])
        elif trial_info['TYPE'] == Trial_type.training or trial_info['TYPE'] == Trial_type.experiment:
            trial = Trial(time=trial_info['SHOW_TIME'], per=Per.small, rel=trial_info['RELATIONS'],
                          feedb=trial_info['FEEDB'], wait=trial_info['WAIT_TIME'], exp=trial_info['TYPE'],
                          tip=trial_info.get('TIP'), tip_time=trial_info['TIP_TIME'], answers=trial_info['ANSWERS'])
        else:
            print trial_info['TYPE']
            raise AssertionError("wrong trial type")

        experiment.list_of_blocks[block_number - 1].list_of_experiment_elements.append(trial)

    if randomize:
        experiment.randomize()
    experiment.save()
