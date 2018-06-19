import re


class CHATCleaner:
    """Perform cleaning on the tiers of CHAT.

    Note:
        The order of calling the cleaning methods has great impact on the final
        result, e.g. handling of repetitions has be done first, before scoped
        symbols are removed.
    """

    def _remove_redundant_whitespaces(self, utterance):
        """Remove redundant whitespaces in utterances.

        This method is routinely called by most of the cleaning methods.
        """
        whitespace_regex = re.compile(r'\s+')
        return whitespace_regex.sub(' ', utterance)

    def remove_terminator(self, utterance):
        """Remove the terminator from the utterance.

        There are 13 different terminators in CHAT. Coding: [+/.!?"]*[!?.]  .
        """
        # postcodes or nothing may follow terminators
        terminator_regex = re.compile(r'[+/.!?"]*[!?.](?=( \[\+|$))')
        clean1 = terminator_regex.sub('', utterance)
        clean2 = self._remove_redundant_whitespaces(clean1)
        return clean2

    def null_untranscribed_utterances(self, utterance):
        """Null utterances containing only untranscribed material.

        Note:
            Nulling means here the utterance is returned as an empty string.
        """
        if utterance == 'xxx':
            return ''
        else:
            return utterance

    def null_event_utterances(self, utterance):
        """Null utterances that are events.

        CHAT coding: 0
        """
        if utterance == '0':
            return ''
        else:
            return utterance

    def remove_events(self, utterance):
        """Remove events from the utterance.

        Coding in CHAT: word starting with &=.
        """
        event_regex = re.compile(r'&=\S+')
        clean1 = event_regex.sub('', utterance)
        clean2 = self._remove_redundant_whitespaces(clean1)
        return clean2

    def handle_repetitions(self, utterance):
        """Write out repeated words in the utterance.

        Coding in CHAT: [x <number>]  .
        """
        repetition_regex = re.compile(r'(?:<(.*?)>|(\S+)) \[x (\d)\]')
        # build cleaned utterance
        clean = ''
        match_end = 0
        for match in repetition_regex.finditer(utterance):
            # add material preceding match
            match_start = match.start()
            clean += utterance[match_end:match_start]

            # check whether it has scope over one or several words
            if match.group(1):
                words = match.group(1)
            else:
                words = match.group(2)

            # repeat the word
            repetitions = int(match.group(3))
            clean += ' '.join([words]*repetitions)

            match_end = match.end()

        # add material following last match
        clean += utterance[match_end:]

        if clean:
            return clean
        else:
            return utterance

    def remove_omissions(self, utterance):
        """Remove omissions in the utterance.

        Coding in CHAT: word starting with 0.
        """
        omission_regex = re.compile(r'0\S+')
        clean1 = omission_regex.sub('', utterance)
        clean2 = self._remove_redundant_whitespaces(clean1)
        return clean2

    def unify_untranscribed(self, utterance):
        """Unify untranscribed material as xxx.

        Coding in CHAT: xxx, yyy, www   .
        """
        untranscribed_regex = re.compile(r'yyy|www')
        return untranscribed_regex.sub('xxx', utterance)

    def get_shortening_actual(self, utterance):
        """Get the actual form of shortenings.

        Coding in CHAT: parentheses within word.
        The part with parentheses is removed.
        """
        shortening_regex = re.compile(r'(\S*)\(\S+\)(\S*)')
        return shortening_regex.sub(r'\1\2', utterance)

    def get_shortening_target(self, utterance):
        """Get the target form of shortenings.

        Coding in CHAT: \w+(\w+)\w+ .
        The part in parentheses is kept, parentheses are removed.
        """
        shortening_regex = re.compile(r'(\S*)\((\S+)\)(\S*)')
        return shortening_regex.sub(r'\1\2\3', utterance)

    def get_replacement_actual(self, utterance):
        """Get the actual form of replacements.

        Coding in CHAT: [: <words>] .
        Keeps replaced words, removes replacing words with brackets.
        """
        # several scoped words
        replacement_regex2 = re.compile(r'<(.*?)> \[: .*?\]')
        clean1 = replacement_regex2.sub(r'\1', utterance)
        # one scoped word
        replacement_regex1 = re.compile(r'(\S+) \[: .*?\]')
        return replacement_regex1.sub(r'\1', clean1)

    def get_replacement_target(self, utterance):
        """Get the target form of replacements.

        Coding in CHAT: [: <words>] .
        Removes replaced words, keeps replacing words with brackets.
        """
        replacement_regex = re.compile(r'(?:<.*?>|\S+) \[: (.*?)\]')
        return replacement_regex.sub(r'\1', utterance)

    def get_fragment_actual(self, utterance):
        """Get the actual form of fragments.

        Coding in CHAT: word starting with &.
        Keeps the fragment, removes the & from the word.
        """
        fragment_regex = re.compile(r'&(\S+)')
        return fragment_regex.sub(r'\1', utterance)

    def get_fragment_target(self, utterance):
        """Get the target form of fragments.

        Coding in CHAT: word starting with &.
        The fragment is marked as untranscribed (xxx).
        """
        fragment_regex = re.compile(r'&\S+')
        return fragment_regex.sub('xxx', utterance)

    def remove_form_markers(self, utterance):
        """Remove form markers from the utterance.

        Coding in CHAT: word ending with @.
        The @ and the part after it are removed.
        """
        form_marker_regex = re.compile(r'(\S+)@\S+')
        return form_marker_regex.sub(r'\1', utterance)

    def remove_linkers(self, utterance):
        """Remove linkers from the utterance.

        Coding in CHAT: +["^,+<] (always in the beginning of utterance).
        """
        linker_regex = re.compile(r'^\+["^,+<]')
        return linker_regex.sub('', utterance).lstrip(' ')

    def remove_separators(self, utterance):
        """Remove separators from the utterance.

        Separators are commas, colons or semi-colons which are surrounded
        by whitespaces.
        """
        separator_regex = re.compile(r' [,:;]( )')
        return separator_regex.sub(r'\1', utterance)

    def remove_ca(self, utterance):
        """Remove conversation analysis and satellite markers from utterance.

        Note:
            Only four markers (↓↑‡„) are attested in the corpora. Only those
            will be checked for removal.
        """
        ca_regex = re.compile(r'[↓↑‡„]')
        clean1 = ca_regex.sub('', utterance)
        clean2 = self._remove_redundant_whitespaces(clean1)
        return clean2

    def remove_fillers(self, utterance):
        """Remove fillers from the utterance.

        Coding in CHAT: word starts with &-
        """
        filler_regex = re.compile(r'&-(\S+)')
        return filler_regex.sub(r'\1', utterance)

    def remove_pauses_within_words(self, utterance):
        """Remove pauses within words from the utterance.

        Coding in CHAT: ^ within word
        """
        pause_regex = re.compile(r'(\S+)\^(\S+)')
        return pause_regex.sub(r'\1\2', utterance)

    def remove_blocking(self, utterance):
        """Remove blockings in words from the utterance.

        Coding in CHAT: ^ at the beginning of the word
        """
        blocking_regex = re.compile(r'\^(\S+)')
        return blocking_regex.sub(r'\1', utterance)

    def remove_pauses_between_words(self, utterance):
        """Remove pauses between words from the utterance.

        Coding in CHAT: (.), (..), (...)
        """
        pause_regex = re.compile(r'\(\.{1,3}\)')
        clean1 = pause_regex.sub('', utterance)
        clean2 = self._remove_redundant_whitespaces(clean1)
        return clean2

    def remove_drawls(self, utterance):
        """Remove drawls from the utterance.

        Coding in CHAT: : within or after word
        """
        drawl_regex = re.compile(r'(\S+):(\S+)?')
        return drawl_regex.sub(r'\1\2', utterance)

    # TODO: handle nested scopes
    def remove_scoped_symbols(self, utterance):
        """Remove scoped symbols from utterance.

        Coding in CHAT: < > [.*]    .

        Note:
            Nested scopes are only checked with depth 1.
            Ex. <<ıspanak bitmediyse de> [/-] yemesin> [<].
        """
        # several scoped words
        scope_regex1 = re.compile(r'<(.*?)> \[.*?\]')
        clean1 = scope_regex1.sub(r'\1', utterance)
        # one scoped word
        scope_regex2 = re.compile(r'(\S+) \[.*?\]')
        clean2 = scope_regex2.sub(r'\1', clean1)
        clean3 = self._remove_redundant_whitespaces(clean2)
        return clean3


if __name__ == '__main__':
    cleaner = CHATCleaner()
    print(repr(cleaner._remove_redundant_whitespaces('Das   ist zu  viel.')))
    print(repr(cleaner.remove_terminator('doa to: (.) mado to: +... [+ bch]')))
    print(repr(cleaner.null_untranscribed_utterances('xxx')))
    print(repr(cleaner.null_event_utterances('0')))
    print(repr(cleaner.remove_events('I know &=laugh what that &=laugh means .')))
    print(repr(cleaner.handle_repetitions('This <is a> [x 3] sentence [x 2].')))
    print(repr(cleaner.remove_omissions('This is 0not 0good .')))
    print(repr(cleaner.unify_untranscribed('This www I yyy is done .')))
    print(repr(cleaner.get_shortening_actual('This (i)s a short(e)ned senten(ce)')))
    print(repr(cleaner.get_shortening_target('This (i)s a short(e)ned senten(ce)')))
    print(repr(cleaner.get_replacement_actual('This us [: is] <srane suff> [: strange stuff]')))
    print(repr(cleaner.get_replacement_target('This us [: is] <srane suff> [: strange stuff]')))
    print(repr(cleaner.get_fragment_actual('This is &at .')))
    print(repr(cleaner.get_fragment_target('This is &at .')))
    print(repr(cleaner.remove_form_markers('I know the A@l B@l C@l .')))
    print(repr(cleaner.remove_linkers('+" bir de köpek varmış .')))
    print(repr(cleaner.remove_separators('that is , that is ; that is : that is .')))
    print(repr(cleaner.remove_ca('up ↑ and down ↓ .')))
    print(repr(cleaner.remove_fillers('&-um what &-um is that &-um .')))
    print(repr(cleaner.remove_pauses_within_words('Th^is is a com^puter .')))
    print(repr(cleaner.remove_pauses_between_words('This (.) is (..) a (...) sentence .')))
    print(repr(cleaner.remove_drawls('Thi:s is tea: .')))
    print(repr(cleaner.remove_scoped_symbols('ji [=! smiling] '
                                             '<take your shoes off> [!] '
                                             '(w)a [!!] '
                                             'Maks [= the name of CHIs dog] '
                                             'dur silim [: sileyim] '
                                             'dici [=? dizi] '
                                             '<Ekin beni yakalayamaz> [% said with singing] '
                                             'mami cuando [?] '
                                             'oturduğun [>1] '
                                             '<lana lana> [/] lana '
                                             'qaigu [//] qainngitualuk '
                                             'sen niye bozdun [///] kim bozdu '
                                             '<<ıspanak bitmediyse de> [/-] yemesin> [<] '
                                             'blubla [*]')))
