import itertools
import contextlib
import mmap
import re


class CHATReader:
    """Parser for CHAT metadata and records of a session."""

    # utterance ID
    uid = None

    @classmethod
    def get_uid(cls):
        """Get the utterance ID.

        The ID counter is generated by the method 'iter_records' that
        increments the counter by one for each record.

        Returns:
            str: The utterance ID consisting of 'u' + the ID counter.
            None: If method 'iter_records' has not been called yet.
        """
        if cls.uid is not None:
            return 'u' + cls.uid

    # ---------- session processing ----------

    @staticmethod
    def get_metadata(session_path):
        """Get the metadata of a session."""
        pass

    @classmethod
    def iter_records(cls, session_path):
        """Yield a record of the CHAT file.

        A record starts with ``*speaker_label:\t`` in CHAT.

        Yields:
            str: The next record.
        """
        # for utterance ID generation
        counter = itertools.count()
        cls.uid = next(counter)

        with open(session_path, 'rb') as f:
            # use memory-mapping of files
            with contextlib.closing(
                    mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)) as text:

                # create a record generator
                rec_generator = re.finditer(br'\*[A-Z]{3}:\t', text)

                # get start of first record
                rec_start_pos = next(rec_generator).start()

                # iter all records
                for rec in rec_generator:

                    # get start of next record
                    next_rec_start_pos = rec.start()

                    # get the stringified record
                    rec_str = text[rec_start_pos:next_rec_start_pos].decode()

                    yield rec_str

                    cls.uid = next(counter)

                    # set new start of record
                    rec_start_pos = next_rec_start_pos

                # handle last record
                rec_str = text[rec_start_pos:].decode()
                yield rec_str

                cls.uid = None

    # ---------- record processing ----------

    @staticmethod
    def remove_line_breaks(rec):
        """Remove line breaks within the tiers of a record.

        CHAT inserts line breaks when the text of a main line or dependent
        tier becomes too long.

        Args:
            rec (str): The record.

        Returns:
            str: Record without break lines within the tiers.
        """
        return rec.replace('\n\t', ' ')

    @classmethod
    def get_main_line(cls, rec):
        """Get the main line of the record."""
        rec = cls.remove_line_breaks(rec)
        main_line_regex = re.compile(r'\*[A-Z]{3}:\t.*')
        return main_line_regex.search(rec).group()

    @staticmethod
    def get_dependent_tier(rec, name):
        """Get the content of the dependent tier from the record.

        Args:
            rec (str): The record.
            name (str): The name of the dependent tier.

        Returns:
            str: The content of the dependent tier.
            None: If there is no dependent tier called 'name' in the record.
        """
        dependent_tier_regex = re.compile(r'%{}:\t(.*)'.format(name))
        match = dependent_tier_regex.search(rec)
        if match is not None:
            return match.group(1)

    @classmethod
    def get_addressee(cls, rec):
        """Get the addressee of the record.

        Returns:
            str: The content of the 'add' dependent tier.
            None: If there is no dependent tier called 'add' in the record.
        """
        return cls.get_dependent_tier(rec, 'add')

    @classmethod
    def get_translation(cls, rec):
        """Get the translation of the record.

        Returns:
            str: The content of the 'eng' dependent tier.
            None: If there is no dependent tier called 'eng' in the record.
        """
        return cls.get_dependent_tier(rec, 'eng')

    @classmethod
    def get_comments(cls, rec):
        """Get the comments of a record.

        Returns:
            str: The content of the 'com' dependent tier.
            None: If there is no dependent tier called 'com' in the record.
        """
        return cls.get_dependent_tier(rec, 'com')

    @staticmethod
    def get_seg_tier(rec):
        """Get the tier containing segments."""
        raise NotImplementedError

    @staticmethod
    def get_gloss_tier(rec):
        """Get the tier containing glosses."""
        raise NotImplementedError

    @staticmethod
    def get_pos_tier(rec):
        """Get the tier containing POS tags."""
        raise NotImplementedError

    # ---------- main line processing ----------

    @staticmethod
    def get_speaker_label(main_line):
        """Get the speaker label from the main line.

        Args:
            main_line (str): The main line.

        Returns:
            str: The speaker label.

        """
        speaker_label_regex = re.compile(r'(?<=^\*)[A-Z]{3}')
        return speaker_label_regex.search(main_line).group()

    @staticmethod
    def get_utterance(main_line):
        """Get the utterance from the main line.

        Args:
            main_line (str): The main line.

        Returns:
            str: The utterance.
        """
        utterance_regex = re.compile(r'(?<=:\t).*[.!?]')
        return utterance_regex.search(main_line).group()

    @staticmethod
    def get_time(main_line):
        """Get the time from the main line.

        Args:
            main_line (str): The main line.

        Returns:
            str: The time consisting of start and end time.
        """
        time_regex = re.compile(r'\d+_\d+')
        match = time_regex.search(main_line)
        if match is None:
            return ''
        else:
            return match.group()

    # ---------- utterance processing ----------

    @staticmethod
    def get_words(utterance):
        """Get the words of an utterance.

        Returns:
            list: The words of an utterance.
        """
        return [word for word in utterance.split(' ')]

    @staticmethod
    def get_shortening_actual(utterance):
        """Get the actual form of shortenings.

        Coding in CHAT: parentheses within word.
        The part with parentheses is removed.
        """
        shortening_regex = re.compile(r'(\S*)\(\S+\)(\S*)')
        return shortening_regex.sub(r'\1\2', utterance)

    @staticmethod
    def get_shortening_target(utterance):
        """Get the target form of shortenings.

        Coding in CHAT: \w+(\w+)\w+ .
        The part in parentheses is kept, parentheses are removed.
        """
        shortening_regex = re.compile(r'(\S*)\((\S+)\)(\S*)')
        return shortening_regex.sub(r'\1\2\3', utterance)

    @staticmethod
    def get_replacement_actual(utterance):
        """Get the actual form of replacements.

        Coding in CHAT: [: <words>] .
        Keeps replaced words, removes replacing words with brackets.
        """
        # several scoped words
        replacement_regex1 = re.compile(r'<(.*?)> \[: .*?\]')
        clean = replacement_regex1.sub(r'\1', utterance)
        # one scoped word
        replacement_regex2 = re.compile(r'(\S+) \[: .*?\]')
        return replacement_regex2.sub(r'\1', clean)

    @staticmethod
    def get_replacement_target(utterance):
        """Get the target form of replacements.

        Coding in CHAT: [: <words>] .
        Removes replaced words, keeps replacing words with brackets.
        """
        replacement_regex = re.compile(r'(?:<.*?>|\S+) \[: (.*?)\]')
        return replacement_regex.sub(r'\1', utterance)

    @staticmethod
    def get_fragment_actual(utterance):
        """Get the actual form of fragments.

        Coding in CHAT: word starting with &.
        Keeps the fragment, removes the & from the word.
        """
        fragment_regex = re.compile(r'&(\S+)')
        return fragment_regex.sub(r'\1', utterance)

    @staticmethod
    def get_fragment_target(utterance):
        """Get the target form of fragments.

        Coding in CHAT: word starting with &.
        The fragment is marked as untranscribed (xxx).
        """
        fragment_regex = re.compile(r'&\S+')
        return fragment_regex.sub('xxx', utterance)

    @classmethod
    def get_actual_form(cls, utterance):
        """Get the actual form of the utterance."""
        for actual_method in [cls.get_shortening_actual,
                              cls.get_fragment_actual,
                              cls.get_replacement_actual]:
            utterance = actual_method(utterance)

        return utterance

    @classmethod
    def get_target_form(cls, utterance):
        """Get the target form of the utterance."""
        for target_method in [cls.get_shortening_target,
                              cls.get_fragment_target,
                              cls.get_replacement_target]:
            utterance = target_method(utterance)

        return utterance

    @staticmethod
    def get_sentence_type(utterance):
        """Get the sentence type of an utterance.

        The sentence type is inferred from the utterance terminator.
        """
        mapping = {'.': 'declarative',
                   '?': 'question',
                   '!': 'exclamation',
                   '+.': 'broken for coding',
                   '+..': 'trail off',
                   '+..?': 'trail off of question',
                   '+!?': 'question with exclamation',
                   '+/.': 'interruption',
                   '+/?': 'interruption of a question',
                   '+//.': 'self-interruption',
                   '+//?': 'self-interrupted question',
                   '+"/.': 'quotation follows',
                   '+".': 'quotation precedes'}
        terminator_regex = re.compile(r'([+/.!?"]*[!?.])(?=( \[\+|$))')
        match = terminator_regex.search(utterance)
        return mapping[match.group(1)]

    # ---------- time processing ----------

    @staticmethod
    def get_start(rec_time):
        """Get the start time from the time.

        Args:
            rec_time (str): The time.

        Returns:
            str: The start time.
        """
        if not rec_time:
            return rec_time
        else:
            start_regex = re.compile(r'(\d+)_')
            return start_regex.search(rec_time).group(1)

    @staticmethod
    def get_end(rec_time):
        """Get the end time from the time.

        Args:
            rec_time (str): The time.

        Returns:
            str: The end time.
        """
        if not rec_time:
            return rec_time
        else:
            end_regex = re.compile(r'_(\d+)')
            return end_regex.search(rec_time).group(1)

    # ---------- morphology processing ----------

    @classmethod
    def get_seg_words(cls, seg_tier):
        """Get the words from the segment tier."""
        return cls.get_words(seg_tier)

    @classmethod
    def get_gloss_words(cls, gloss_tier):
        """Get the words from the gloss tier."""
        return cls.get_words(gloss_tier)

    @classmethod
    def get_pos_words(cls, pos_tier):
        """Get the words from the POS tag tier."""
        return cls.get_words(pos_tier)

    @staticmethod
    def get_segments(seg_word):
        """Get the segments from the segment word."""
        raise NotImplementedError

    @staticmethod
    def get_glosses(gloss_word):
        """Get the glosses from the gloss word."""
        raise NotImplementedError

    @staticmethod
    def get_poses(pos_word):
        """Get the POS tags from the POS word."""
        raise NotImplementedError

###############################################################################


class InuktitutReader(CHATReader):
    """Inferences for Inuktitut."""

    @staticmethod
    def get_actual_alternative(utterance):
        """Get the actual form of alternatives.

        Coding in CHAT: [=? <words>]
        The actual form is the alternative given in brackets.
        """
        replacement_regex = re.compile(r'(?:<.*?>|\S+) \[=\? (.*?)\]')
        return replacement_regex.sub(r'\1', utterance)

    @staticmethod
    def get_target_alternative(utterance):
        """Get the target form of alternatives.

        Coding in CHAT: [=? <words>]
        The target form is the original form.
        """
        # several scoped words
        alternative_regex1 = re.compile(r'<(.*?)> \[=\? .*?\]')
        clean = alternative_regex1.sub(r'\1', utterance)
        # one scoped word
        alternative_regex2 = re.compile(r'(\S+) \[=\? .*?\]')
        return alternative_regex2.sub(r'\1', clean)

    @classmethod
    def get_actual_form(cls, utterance):
        """Get the actual form of the utterance.

        Considers alternatives as well.
        """
        utterance = super().get_actual_form(utterance)
        return cls.get_actual_alternative(utterance)

    @classmethod
    def get_target_form(cls, utterance):
        """Get the target form of the utterance.

        Considers alternatives as well.
        """
        utterance = super().get_target_form(utterance)
        return cls.get_target_alternative(utterance)

    @classmethod
    def get_seg_tier(cls, rec):
        return cls.get_dependent_tier(rec, 'xmor')

    @classmethod
    def get_gloss_tier(cls, rec):
        return cls.get_dependent_tier(rec, 'xmor')

    @classmethod
    def get_pos_tier(cls, rec):
        return cls.get_dependent_tier(rec, 'xmor')

    @staticmethod
    def iter_morphemes(word):
        """Iter POS tags, segments and glosses of a word.

        Args:
            word (str): A morpheme word.

        Yields:
            tuple: The next POS tag, segment and gloss in the word.
        """
        morpheme_regex = re.compile(r'(.*)\|(.*?)\^(.*)')
        for morpheme in word.split('+'):
            match = morpheme_regex.search(morpheme)
            yield match.group(1), match.group(2), match.group(3)

    @classmethod
    def get_segments(cls, seg_word):
        return [seg for _, seg, _ in cls.iter_morphemes(seg_word)]

    @classmethod
    def get_glosses(cls, gloss_word):
        return [gloss for _, _, gloss in cls.iter_morphemes(gloss_word)]

    @classmethod
    def get_poses(cls, pos_word):
        return [pos for pos, _, _ in cls.iter_morphemes(pos_word)]


class CreeReader(CHATReader):

    @classmethod
    def get_seg_tier(cls, rec):
        return cls.get_dependent_tier(rec, 'xactmor')

    @classmethod
    def get_gloss_tier(cls, rec):
        return cls.get_dependent_tier(rec, 'xmormea')

    @classmethod
    def get_pos_tier(cls, rec):
        return cls.get_dependent_tier(rec, 'xmortyp')


def main():
    import glob
    import acqdiv
    import os
    import time

    # start_time = time.time()
    #
    # acqdiv_path = os.path.dirname(acqdiv.__file__)
    # corpora_path = os.path.join(acqdiv_path, 'corpora/*/cha/*.cha')
    #
    # for path in glob.iglob(corpora_path):
    #
    #     chat_parser = CHATParser()
    #
    #     for rec in chat_parser.iter_records(path):
    #         main_line = chat_parser.get_main_line(rec)
    #         speaker_label = chat_parser.get_speaker_label(main_line)
    #         utterance = chat_parser.get_utterance(main_line)
    #         rec_time = chat_parser.get_time(main_line)
    #         start = chat_parser.get_start(rec_time)
    #         end = chat_parser.get_end(rec_time)
    #
    # print('--- %s seconds ---' % (time.time() - start_time))

    parser = CHATReader()
    print(repr(parser.get_shortening_actual(
        'This (i)s a short(e)ned senten(ce)')))
    print(repr(parser.get_shortening_target(
        'This (i)s a short(e)ned senten(ce)')))
    print(repr(parser.get_replacement_actual(
        'This us [: is] <srane suff> [: strange stuff]')))
    print(repr(parser.get_replacement_target(
        'This us [: is] <srane suff> [: strange stuff]')))
    print(repr(parser.get_fragment_actual('This is &at .')))
    print(repr(parser.get_fragment_target('This is &at .')))
    print(repr(parser.get_sentence_type('This is a sent +!?')))

    inuktitut_parser = InuktitutReader()
    print(repr(inuktitut_parser.get_actual_alternative(
        'This is the target [=? actual] form.')))
    print(repr(inuktitut_parser.get_target_alternative(
        'This is the target [=? actual] form.')))

    test = 'LR|qa^outside+LI|unnga^ALL+VZ|aq^go_by_way_of+VV|VA|' \
           'tit^CAUS+VV|lauq^POL+VI|nnga^IMP_2sS_1sO VR|' \
           'nimak^move_around+VV|VA|tit^CAUS+VV|nngit^NEG+VI|' \
           'lugu^ICM_XxS_3sO? VR|kuvi^pour+NZ|suuq^HAB+NN|AUG|aluk^EMPH?'

    for word in inuktitut_parser.get_words(test):
        for morpheme in inuktitut_parser.iter_morphemes(word):
            print(repr(morpheme))


if __name__ == '__main__':
    main()