"""
This module provides a class for propagating changes in corpus files according
to the log and dictionary files. The following files are used and their paths:
    - corpus files
    - normal/vt dictionary
    - normal/vt log
"""
import os
import re
import logging
from collections import OrderedDict


class CorpusPropagater:
    """Class for propagting changes in dictionary in corpus."""

    # paths to dictionary, log and corpus files
    org_cp_path = "cp/corpus"
    new_cp_path = "cp/corpus_new"
    dic_path = "cp/DeneDic.txt"
    vtdic_path = "cp/DeneVTDic.txt"
    log_path = "cp/DeneLog.txt"
    vtlog_path = "cp/DeneVTLog.txt"

    def __init__(self):
        """Initialize dictionaries, logs and and utterance hash."""
        self.vtdic = {}
        self.dic = {}
        self.logs = {}
        self.vtlogs = {}

        # save data of one utterance using a sorted dict because order is
        # important; key is the fieldmarker, value the whole line (including
        # field marker label) except for \glo, \seg, \id which are
        # temporarily saved in a special data structure under "words"
        self.ref_dict = OrderedDict()
        # if \ref has errors in it
        self.has_errors = False

    def activate_logger(self):
        """Activate logger."""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        handler = logging.FileHandler("cp.log", mode="w")
        handler.setLevel(logging.WARNING)

        formatter = logging.Formatter("%(funcName)s|%(levelname)s|%(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def get_dic_data(self, is_vtdic=False):
        """Collect data from a dictionary.

        is_vtdic (bool): verb theme dictionary or not
        """
        # check which dictionary type should be processed
        if is_vtdic:
            dic = self.vtdic
            path = self.vtdic_path
        else:
            dic = self.dic
            path = self.dic_path

        # check if path is valid
        if not os.path.isfile(path):
            print("Path '{}' for dictionary file does not exist".format(path))
            print()
            return

        with open(path, "r") as dic_file:

            # iterate file line by line
            for line in dic_file:

                line = line.rstrip()

                # if start of lemma entry is found
                if "\\lem" in line:
                    if is_vtdic:
                        # get lemma which becomes the id
                        id = line.split()[1]
                        # create entry in dic with this lemma as key
                        dic[id] = {}
                    else:
                        # get id of this lemma which is the next line
                        id = next(dic_file).split()[1]
                        # create entry in dic with this id as key
                        dic[id] = {}
                        # add the lemma
                        dic[id]["lem"] = line.split()[1]

                    # initialize glosses as empty list
                    dic[id]["glo"] = []

                elif "\\glo" in line:
                    dic[id]["glo"].append(line.split()[1])

    def get_log_data(self, is_vtlog=False):
        """Collect data from log file.

        is_vtlog (bool): verb theme log or not
        """
        if is_vtlog:
            path = self.vtlog_path
            logs = self.vtlogs
        else:
            path = self.log_path
            logs = self.logs

        # check if path is valid
        if not os.path.isfile(path):
            print("Path '{}' for log file does not exist".format(path))
            print()
            return

        with open(path, "r") as log_file:

            for line in log_file:
                # get log as a list of data
                log = line.rstrip().split("|")
                # UPDATE/MERGE/SPLIT
                cmd = log[0].upper()
                # affected id (log) or lemma (vtlog)
                id = log[1]
                # initialze log hash with id/lemma as key if necessary
                if id not in logs:
                    logs[id] = []

                # format for UPDATE: UPDATE|id|tier==old|new
                if cmd == "UPDATE":
                    # get tier (seg|glo|vtg) and old seg/glo/vtg value
                    tier, old = re.split("==", log[2])
                    # add under correct id to logs
                    logs[id].append({"cmd": cmd, "tier": tier,
                                     "old": old, "new": log[3]})
                # format for MERGE: MERGE|old_id|new_id
                elif cmd == "MERGE":
                    logs[id].append({"cmd": cmd, "new_id": log[2]})

                # format for SPLIT: SPLIT|old_id|new_id|tier==criterion
                elif cmd == "SPLIT":
                    # get tier (full|glo|vtg) and criterion value
                    tier, criterion = re.split("==", log[3])
                    logs[id].append({"cmd": cmd, "new_id": log[2],
                                     "tier": tier, "criterion": criterion})
                else:
                    self.logger.error("Command {} not defined.".format(cmd))

    def collect_data(self):
        """Collect data from dictionary and log files."""
        self.get_dic_data()
        self.get_dic_data(is_vtdic=True)
        self.get_log_data()
        self.get_log_data(is_vtlog=True)

    def process_corpus(self):
        """Process every corpus file."""
        # first create directory for the new corpus files
        if not os.path.isdir(self.new_cp_path):
            try:
                os.mkdir(self.new_cp_path)
            except FileNotFoundError:
                print("Path '{}' for corpus directory does not exist".format(
                      self.new_cp_path))
                print()
                return

        # go through each original corpus file
        for file in os.listdir(self.org_cp_path):

            # if it is a toolbox file
            if file.endswith(".tbt"):

                # get path of this original file
                org_file_path = os.path.join(self.org_cp_path, file)

                # get path for new corpus file
                new_file_path = os.path.join(self.new_cp_path, file)

                # then open original file for reading and new file for writing
                with open(org_file_path, "r") as self.org_file, \
                     open(new_file_path, "w") as self.new_file:

                    self.process_file()

    def process_file(self):
        """Read data of utterances and process them."""
        # reset
        self.ref_dict.clear()
        self.has_errors = False

        # go through all data fomr a corpus file
        # and save data per utterance unter ref_dict
        for line in self.org_file:

            # throw away the newline at the end of a line
            line = line.rstrip("\n")

            # if new utterance starts
            if line.startswith("\\ref"):
                # process previous utterance
                self.process_utterance()
                # reset to False
                self.has_errors = False
                # reset no. words
                n_words = 0
                # delete data of previous utterance
                self.ref_dict.clear()
                # add \ref to hash
                self.ref_dict["\\ref"] = line

            # if fieldmarker \full of utterance starts
            elif line.startswith("\\full"):

                has_label = self.process_tier(line)[2]

                if not has_label:
                    # save morpheme data in a special data structure
                    # words: [(word1, {"\\seg": [seg1, seg2]
                    #                  "\\glo": [glo1, glo2],
                    #                  "\\id": [id1, id2]}), (word2, {...})]
                    self.ref_dict["words"] = []

                # extract words splitting the processed line at whitespaces
                word_iterator = re.finditer(r"\S+", line)
                # skip the field marker label
                next(word_iterator)

                # add every word to the hash
                for word in word_iterator:
                    self.ref_dict["words"].append((word.group(), {}))
                    n_words += 1

            # if any field marker starts
            elif line.startswith("\\"):

                label, data, has_label = self.process_tier(line)

                # deal with morpheme tiers separately
                if label in {"\\seg", "\\glo", "\\id", "\\vt", "\\vtg"}:

                    # get regex & iterator for extracting units per word
                    regex = re.compile(r"((\S+-\s+)*\S+(\s+-\S+)*)")
                    unitgroup_iterator = regex.finditer(line)

                    # get field marker label which is the first unit
                    label = next(unitgroup_iterator).group()

                    # find out no. of unit groups so far inserted for this tier
                    n_unitgroups = 0
                    if has_label:
                        for word, morphemes in self.ref_dict["words"]:
                            if label in morphemes:
                                n_unitgroups += 1

                    # go over those units per word
                    for i, unitgroup in enumerate(unitgroup_iterator,
                                                  start=n_unitgroups):

                        n_unitgroups += 1

                        # extract units of a unitgroup splitting at whitespaces
                        units = re.split("\s+", unitgroup.group())

                        try:
                            # add units to the right word (via index)
                            # to morpheme dictionary (at index 1)
                            # under the right label (\seg,\glo,\id,\vt,\vtg)
                            self.ref_dict["words"][i][1][label] = units

                        # if there are less words than unit groups
                        except IndexError:
                            # add it under an empty word
                            self.ref_dict["words"].append(("", {label: units}))

                    # log it if number of words and unit groups is not equal
                    if n_words != n_unitgroups:
                        self.logger.error(
                            "no. unit groups and words unequal for {}".
                            format(self.ref_dict["\\ref"]))
                        self.has_errors = True

            # if line does not start with \\, its data must belong
            # to the fieldmarker that directly comes before
            elif line:
                # get last added fieldmarker
                label = next(reversed(self.ref_dict))
                # concatenate content
                self.ref_dict[label] += line

        # check last ref inserted
        self.process_utterance()

    def process_tier(self, line):
        """Extract label and data and check if label is already in ref_dict.

        line (str): tier
        """
        # extract field marker label and its data
        match = re.match(r"(\\\w+)(.*)", line)

        label = match.group(1)
        data = match.group(2)

        # field marker in ref_dict
        has_label = False

        # check if there are several defintions of the
        # same fieldmarker in one \ref
        if label in self.ref_dict:
            has_label = True
            # concatenate with hash content
            self.ref_dict[label] += data
        else:
            # add to hash
            self.ref_dict[label] = line

        return (label, data, has_label)

    def process_utterance(self):
        """Check utterance for errors and ids and lemmas in the logs."""

        # if utterance has errors or no words in it, write directly to file
        if self.has_errors or "words" not in self.ref_dict:
            return self.write_file()

        # for logging purposes
        ref = self.ref_dict["\\ref"]

        # check all words for ids in log
        for word, morphemes in self.ref_dict["words"]:

            # check if there is morpheme data
            if not morphemes:
                self.logger.info("missing morpheme data for {}".format(ref))
                self.has_errors = True
                return self.write_file()

            # check if all morpheme tiers are available
            if len(morphemes) != 5:
                self.logger.info("missing tier for {}".format(ref))
                self.has_errors = True
                return self.write_file()

            # check if no. units in this word is equal for all morpheme tiers
            # take no. \seg's as a random reference point
            n_units = len(morphemes["\\seg"])
            for tier in morphemes:
                if len(morphemes[tier]) != n_units:
                    self.logger.error("no. units unequal for {}".format(ref))
                    self.has_errors = True
                    return self.write_file()

            # go through every morpheme id of this word
            for m_pos, m_id in enumerate(morphemes["\\id"]):

                # strip '-' left and right of id (if there is)
                norm_id = m_id.strip("-")

                # do the same for the lemma in \vt
                norm_lem = morphemes["\\vt"][m_pos].strip("-")

                # go through log files
                for key, logs, vt in [(norm_id, self.logs, False),
                                      (norm_lem, self.vtlogs, True)]:

                    # check if id/lemma is in log file
                    if key in logs:

                        # go through all logs with this id/lemma
                        for log in logs[key]:

                            # get command type
                            cmd = log["cmd"].upper()

                            if cmd == "UPDATE":
                                self.update(morphemes, m_pos, log)
                            elif cmd == "MERGE":
                                self.merge(morphemes, m_pos, log, vt)
                            elif cmd == "SPLIT":
                                self.split(word, morphemes, m_pos, log, vt)

        self.write_file()

    def update(self, morphemes, m_pos, log):
        """Update data of a lemma.

        morphemes (hash): morpheme tiers of a word
        m_pos (int): morpheme position in a word
        log (hash): normal/vt log
        """
        # get glo or seg tier
        tier = morphemes["\\" + log["tier"]]
        # change tier at the right position
        if log["old"] in tier[m_pos]:
            tier[m_pos] = tier[m_pos].replace(log["old"], log["new"])

    def sub_ms(self, new, string):
        """Substitute morpheme data in a string.

        new (str): new morpheme value
        string (str): where old morpheme value is replaced by new one
        """
        # regex for replacing morpheme data
        rgx = re.compile(r"(-)?(.*?)(-)?$")
        # replace string (note: \g<> is needed because ids are also integers)
        repl = r"\g<1>{}\g<3>".format(new)

        return rgx.sub(repl, string)

    def merge(self, morphemes, m_pos, log, vt=False):
        """Merge lemma into another.

        morphemes (hash): morpheme tiers of a word
        m_pos (int): morpheme position in a word
        log (hash): normal/vt log
        vt (bool): verbe theme or not
        """
        # id/lemma into which lemma is merged
        key = log["new_id"]

        if vt:
            # check if lemma has an entry in the vt-dictionary
            if key not in self.vtdic:
                self.logger.error("Lemma {} not in vt-dictionary".format(key))
                return

            # adjust \vt
            morphemes["\\vt"][m_pos] = self.sub_ms(key,
                                                   morphemes["\\vt"][m_pos])

            # if original vtg is not in the new dictionary entry
            if morphemes["\\vtg"][m_pos] not in self.vtdic[key]["glo"]:

                # replace by the first vtg of the new dictionary entry
                morphemes["\\vtg"][m_pos] = self.sub_ms(
                    self.vtdic[key]["glo"][0], morphemes["\\vtg"][m_pos])

        else:
            # check if id has an entry in the dictionary
            if key not in self.dic:
                self.logger.error("Id {} not in dictionary".format(key))
                return

            # adjust id and seg
            morphemes["\\id"][m_pos] = self.sub_ms(key,
                                                   morphemes["\\id"][m_pos])

            morphemes["\\seg"][m_pos] = self.sub_ms(self.dic[key]["lem"],
                                                    morphemes["\\seg"][m_pos])

            # if original glo is not in the new dictionary entry
            if morphemes["\\glo"][m_pos] not in self.dic[key]["glo"]:

                # replace by the first gloss of the new dictionary entry
                morphemes["\\glo"][m_pos] = self.sub_ms(
                    self.dic[key]["glo"][0], morphemes["\\glo"][m_pos])

    def split(self, word, morphemes, m_pos, log, vt=False):
        """Split lemma entry into two separate ones.

        word (str): concerned word
        morphemes (hash): morpheme tiers of a word
        m_pos (int): morpheme position in a word
        log (hash): normal/vt log
        vt (bool): verbe theme or not
        """
        # check if criterion for disambiguation is in \full or \glo
        if log["criterion"] in [word, morphemes["\\glo"][m_pos].strip("-")]:

            # merge with data from new entry
            self.merge(morphemes, m_pos, log, vt=vt)

    def write_file(self):
        """Write data of an utterance to the file."""
        # Go through every tier in an utterance
        for tier in self.ref_dict:

            # content of the tier
            content = self.ref_dict[tier]

            # if tier is a morpheme tier
            if tier in {"\\full", "\\seg", "\\glo", "\\id", "\\vt", "\\vtg"}:

                # and the morphemes tiers are unequal in number
                if self.has_errors:
                    # write its content directly to file
                    self.new_file.write(content)
                    # new line after every tier
                    self.new_file.write("\n")

            # if 'words' create its morpheme tiers first before writing
            elif tier == "words":

                # morpheme data is written unchanged (see above)
                if self.has_errors:
                    continue

                # build tiers here
                tiers = OrderedDict([("\\full", "\\full "),
                                     ("\\seg", "\\seg "),
                                     ("\\glo", "\\glo "),
                                     ("\\id", "\\id "),
                                     ("\\vt", "\\vt "),
                                     ("\\vtg", "\\vtg ")])

                # go through each word
                for word, morphemes in content:

                    # concatenate word to tier \full
                    tiers["\\full"] += word

                    # keep track of the longest unit group
                    longest_group = 0
                    # go through each slot in the word (e.g. via \seg)
                    for i, _ in enumerate(morphemes["\\seg"]):

                        # save the no. of chars for every unit in this slot
                        lens = {}

                        # keep track of the longest type of unit
                        longest_unit = 0
                        # go through every type of unit
                        for unit in morphemes:

                            # concatenate unit i to tier of this unit type
                            tiers[unit] += morphemes[unit][i]

                            # save no. of chars of this unit
                            lens[unit] = len(morphemes[unit][i])

                            # compare it to the longest unit seen so far
                            if longest_unit < lens[unit]:
                                longest_unit = lens[unit]

                        # there is one whitespace between morphemes/words
                        longest_unit += 1

                        # add it to the unit group length
                        longest_group += longest_unit

                        # add necessary whitespaces between morphemes
                        for unit in morphemes:
                            tiers[unit] += (longest_unit - lens[unit])*" "

                    # add necessary whitespaces between words
                    tiers["\\full"] += (longest_group - len(word))*" "

                for tier in tiers:
                    # write morpheme tier stripping trailing whitespaces
                    self.new_file.write(tiers[tier].rstrip())
                    # new line after every tier
                    self.new_file.write("\n")

            # any other tier
            else:
                # write its content directly to the file
                self.new_file.write(content)
                # new line after every tier
                self.new_file.write("\n")

        # insert empty line between utterances
        self.new_file.write("\n")

    def propagate(self):
        """Propagate changes in dictionary in corpus."""
        self.activate_logger()
        self.collect_data()
        self.process_corpus()


def main():
    cp = CorpusPropagater()
    cp.propagate()

if __name__ == "__main__":
    main()
