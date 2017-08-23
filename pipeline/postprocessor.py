""" Post-processing processes on the corpora in the ACQDIV-DB. """

import re
import sys
from itertools import groupby

import logging
import pipeline_logging

import sqlalchemy as sa
import database_backend as db

from configparser import ConfigParser
from parsers import CorpusConfigParser
from processors import age

engine = None
conn = None

cleaned_age = re.compile('\d{1,2};\d{1,2}\.\d')
age_pattern = re.compile(".*;.*\..*")
pos_index = {}


def setup(args):
    """ Global setup. """

    global engine, conn

    # Testing mode vs full database.
    if args.t:
        engine = sa.create_engine('sqlite:///database/test.sqlite3')
    else:
        engine = sa.create_engine('sqlite:///database/acqdiv.sqlite3')
    conn = engine.connect()

    # Load the role mapping.ini for unifying roles.
    global roles
    roles = ConfigParser(delimiters=('='))
    roles.optionxform = str
    roles.read("ini/role_mapping.ini")

    # Load the corpus configs.
    global chintang, cree, indonesian, inuktitut, miyata, miipro, russian, sesotho, turkish, yucatec
    chintang = CorpusConfigParser()
    chintang.read("ini/Chintang.ini")
    cree = CorpusConfigParser()
    cree.read("ini/Cree.ini")
    indonesian = CorpusConfigParser()
    indonesian.read("ini/Indonesian.ini")
    inuktitut = CorpusConfigParser()
    inuktitut.read("ini/Inuktitut.ini")
    miyata = CorpusConfigParser()
    miyata.read("ini/Japanese_Miyata.ini")
    miipro = CorpusConfigParser()
    miipro.read("ini/Japanese_MiiPro.ini")
    russian = CorpusConfigParser()
    russian.read("ini/Russian.ini")
    sesotho = CorpusConfigParser()
    sesotho.read("ini/Sesotho.ini")
    turkish = CorpusConfigParser()
    turkish.read("ini/Turkish.ini")
    yucatec = CorpusConfigParser()
    yucatec.read("ini/Yucatec.ini")


def get_config(corpus_name):
    """ Return the config file.
    """
    if corpus_name == "Chintang":
        return chintang
    elif corpus_name == "Cree":
        return cree
    elif corpus_name == "Indonesian":
        return indonesian
    elif corpus_name == "Inuktitut":
        return inuktitut
    elif corpus_name == "Japanese_Miyata":
        return miyata
    elif corpus_name == "Japanese_MiiPro":
        return miipro
    elif corpus_name == "Russian":
        return russian
    elif corpus_name == "Sesotho":
        return sesotho
    elif corpus_name == "Turkish":
        return turkish
    elif corpus_name == "Yucatec":
        return yucatec
    else:
        raise Exception


def main(args):
    """ Global setup and then call post-processes. """
    setup(args)

    with engine.begin() as conn:
        conn.execute('PRAGMA synchronous = OFF')
        conn.execute('PRAGMA journal_mode = MEMORY')
        conn.execution_options(compiled_cache={})

        # Update database tables
        print("Processing speakers table...")
        process_speakers_table()

        print("Processing utterances table...")
        process_utterances_table()

        print("Processing morphemes table...")
        process_morphemes_table()

        print("Processing words table...")
        process_words_table()


def process_speakers_table():
    """ Post-process speakers table. """
    _speakers_indonesian_experimenters()
    _speakers_update_age()
    _speakers_standardize_gender_labels()
    _speakers_standardize_roles()
    _speakers_standardize_macroroles()
    _speakers_get_unique_speakers()
    _speakers_get_target_children()


def _speakers_update_age():
    """ Age standardization. Group by corpus and call age function depending on corpus input format (IMDI of CHAT XML). """
    s = sa.select([db.Speaker.id, db.Speaker.session_id_fk, db.Speaker.corpus, db.Speaker.age_raw, db.Speaker.birthdate])
    query = conn.execute(s)
    for corpus, rows in groupby(query, lambda r: r[2]):
        config = get_config(corpus)
        results = []
        if config["metadata"]["type"] == "imdi":
            results = _update_imdi_age(rows)
        else:
            results = _update_xml_age(rows)
        _update_rows(db.Speaker.__table__, "speaker_id", results)
    query.close()


def _speakers_indonesian_experimenters():
    """ Configuration replacements for Indonesian experimenter speaker labels. Updates the speakers table.  """
    cfg = get_config('Indonesian')
    s = sa.select([db.Speaker.id, db.Speaker.speaker_label, db.Speaker.name]).where(db.Speaker.corpus == 'Indonesian')
    rows = conn.execute(s)
    results = []
    for row in rows:
        if row.speaker_label == 'EXP':
            results.append({'speaker_id': row.id, 'speaker_label': cfg['exp_labels'][row.name]})
    rows.close()
    _update_rows(db.Speaker.__table__, 'speaker_id', results)


def _speakers_standardize_gender_labels():
    """ Standardize gender labels in the speakers table. """
    s = sa.select([db.Speaker.id, db.Speaker.gender_raw])
    rows = conn.execute(s)
    results = []
    for row in rows:
        if row.gender_raw:
            if row.gender_raw.lower() == 'female':
                results.append({'speaker_id': row.id, 'gender': 'Female'})
            elif row.gender_raw.lower() == 'male':
                results.append({'speaker_id': row.id, 'gender': 'Male'})
            else:
                results.append({'speaker_id': row.id, 'gender': 'Unspecified'})
        else:
            results.append({'speaker_id': row.id, 'gender': 'Unspecified'})
    rows.close()
    _update_rows(db.Speaker.__table__, 'speaker_id', results)


def _speakers_standardize_roles():
    """ Unify speaker roles and draw inferences to related values.

    Each corpus has its own set of speaker roles. This function uses
    "role_mapping.ini" to assign a unified role to each speaker according
    to the mappings in role_mapping.ini. The mapping is either based on the original
    role or the speaker_label (depending on how the corpora handles role encoding).
    The role column in the speaker table contains the unified roles.
    """
    s = sa.select([db.Speaker.id, db.Speaker.role_raw, db.Speaker.role, db.Speaker.gender_raw,
                   db.Speaker.gender, db.Speaker.macrorole])
    rows = conn.execute(s)
    results = []
    not_found = set()

    for row in rows:
        role = row.role_raw
        gender = row.gender
        macrorole = row.macrorole

        try:
            role = roles['role_mapping'][row.role_raw]
        except KeyError:
            not_found.add((row.role_raw, row.corpus))  # Otherwise remember role

        # Inference to gender
        if row.gender_raw is None or row.gender_raw in ['Unspecified', 'Unknown']:
            try:
                gender = roles['role2gender'][row.role_raw]
            except KeyError:
                pass

        # Inference to age (-> macrorole)
        if row.macrorole is None or row.macrorole in ['Unspecified', 'Unknown']:
            try:
                macrorole = roles['role2macrorole'][row.role_raw]
                if row.macrorole == 'None':
                    macrorole = None
            except KeyError:
                pass

        for item in not_found:
            logger.warning('\'{}\' from {} not found in role_mapping.ini'.format(item[0], item[1]),
                           exc_info=sys.exc_info())

        results.append({'speaker_id': row.id, 'role': role, 'gender': gender, 'macrorole': macrorole})

    rows.close()
    _update_rows(db.Speaker.__table__, 'speaker_id', results)


def _speakers_standardize_macroroles():
    """ Define macrorole (= Adult, Child, Target_Child, Unknown)

    This function assigns an age category to each speaker. If there is
    no information on age available it uses "role_mappings.ini" to define
    which age category a speaker belongs to. The mapping is based on either
    the speaker's original role or speaker_label (depending on how the corpora
    handles role encoding).
    """
    # TODO: this method is completely dependent on ages -- no warnings are given if the age input is wrong!
    # overwrite role mapping (except target child) if speaker is under 12
    # (e.g. if child is an aunt which is mapped to 'Adult' per default)

    s = sa.select([db.Speaker.id, db.Speaker.corpus, db.Speaker.speaker_label, db.Speaker.age_in_days, db.Speaker.macrorole, db.Speaker.role])
    rows = conn.execute(s)
    results = []

    for row in rows:
        # Adults are >= 12yrs, i.e. > 4380 days.
        if row.age_in_days and row.macrorole != "Target_Child":
            if row.age_in_days <= 4380:
                results.append({'speaker_id': row.id, 'macrorole': "Child"})
            else:
                results.append({'speaker_id': row.id, 'macrorole': "Adult"})

        # Check corpus-specific lists of speaker labels.
        elif row.macrorole is None or row.macrorole == "None":
            try:
                macrorole = "Unknown" if row.macrorole is None or row.macrorole == "None" else roles[row.corpus][row.speaker_label]
                results.append({'speaker_id': row.id, 'macrorole': macrorole})
            except KeyError:
                pass
    rows.close()
    _update_rows(db.Speaker.__table__, 'speaker_id', results)


def _speakers_get_unique_speakers():
    """ Populate the the unique speakers table. Also populate uniquespeaker_id_fk in the speakers table.

    Uniqueness is determined by a combination of corpus, name, speaker label, and birthdate.
    """
    s = sa.select([db.Speaker])
    rows = conn.execute(s)
    unique_speakers = []
    unique_speaker_ids = []
    identifiers = []

    for row in rows:
        t = (row.name, row.birthdate, row.speaker_label, row.corpus)
        if t not in identifiers:
            identifiers.append(t)
            # Create unique speaker rows.
            unique_speaker_id = identifiers.index(t) + 1
            unique_speakers.append({'id': unique_speaker_id, 'corpus': row.corpus, 'speaker_label': row.speaker_label,
                                        'name': row.name, 'birthdate': row.birthdate, 'gender': row.gender})
            unique_speaker_ids.append({'speaker_id': row.id, 'uniquespeaker_id_fk': unique_speaker_id})
    rows.close()
    _update_rows(db.Speaker.__table__, 'speaker_id', unique_speaker_ids)
    _insert_rows(db.UniqueSpeaker.__table__, unique_speakers)


def _speakers_get_target_children():
    """ Set target children for sessions. Also adapt roles and macroroles if there are multiple target children per session.
    """
    s = sa.select([db.Speaker]).where(db.Speaker.role == "Target_Child")
    rows = conn.execute(s)
    targets_per_session = {}
    tc_id_results = []
    non_targets_results = []

    # First store target children per session.
    for row in rows:
        if row.session_id_fk in targets_per_session:
            targets_per_session[row.session_id_fk].add(row.uniquespeaker_id_fk)
        else:
            targets_per_session[row.session_id_fk] = {row.uniquespeaker_id_fk}

    # Second go through all session ids and get the target children for this session.
    for session_id in targets_per_session:
        targets = targets_per_session[session_id]

        # Get session row.
        query = sa.select([db.Session]).where(db.Session.id == session_id)
        rec = conn.execute(query).fetchone()

        # If there is one target child only.
        if len(targets) == 1:
            # Just set target child for the session.
            target_child_fk = targets.pop()
            tc_id_results.append({'session_id': session_id, 'target_child_fk': target_child_fk})

        # If there are several target children infer target child from source id.
        else:
            if rec.corpus == "Chintang":
                # Get target child label and get right target child id.
                label = rec.source_id[2:7]
                tc_id_query = sa.select([db.UniqueSpeaker]).where(sa.and_(
                    db.UniqueSpeaker.corpus == rec.corpus,
                    db.UniqueSpeaker.speaker_label == label))
                tc_id_result = conn.execute(tc_id_query).fetchone()
                tc_id = tc_id_result.id

            elif rec.corpus == "Russian":
                # Session code's first letter matches that of speaker label.
                letter = rec.source_id[0]
                # Get right target child id.
                tc_id_query = sa.select([db.Speaker]).where(sa.and_(
                    db.Speaker.corpus == rec.corpus,
                    db.Speaker.role == "Target_Child",
                    db.Speaker.speaker_label.like("{}%".format(letter))))
                tc_id_result = conn.execute(tc_id_query).fetchone()
                tc_id = tc_id_result.uniquespeaker_id_fk

            elif rec.corpus == "Yucatec":
                label = rec.source_id[:3]
                tc_id_query = sa.select([db.UniqueSpeaker]).where(sa.and_(
                    db.UniqueSpeaker.corpus == rec.corpus,
                    db.UniqueSpeaker.speaker_label == label))
                tc_id_result = conn.execute(tc_id_query).fetchone()
                tc_id = tc_id_result.id

            else:
                logger.warning(
                    "Multiple target children for session {} in {}".format(session_id, rec.corpus))
                continue

            # Set this target child for the session.
            tc_id_results.append({'session_id': session_id, 'target_child_fk': tc_id})

            # Adapt role and macrorole of children that are not target anymore.
            non_targets_query = sa.select([db.Speaker]).where(sa.and_(
                db.Speaker.role == "Target_Child",
                db.Speaker.session_id_fk == session_id,
                db.Speaker.uniquespeaker_id_fk != tc_id))
            non_targets = conn.execute(non_targets_query)

            for row in non_targets:
                non_targets_results.append({'speaker_id': row.id, 'role': "Child", 'macrorole': "Child"})
    rows.close()
    _update_rows(db.Session.__table__, 'session_id', tc_id_results)
    _update_rows(db.Speaker.__table__, 'speaker_id', non_targets_results)


def process_utterances_table():
    """ Post-process utterances table. """
    print("_utterances_standardize_timestamps")
    _utterances_standardize_timestamps()

    print("_utterances_replace_morphemes")
    _utterances_replace_morphemes()

    print("_utterances_change_indonesian_speaker_labels")
    _utterances_change_indonesian_speaker_labels()

    print("_utterances_get_uniquespeaker_ids")
    _utterances_get_uniquespeaker_ids()

    print("_utterances_get_directedness")
    _utterances_get_directedness()


def _utterances_standardize_timestamps():
    """ Unify the time stamps. """
    s = sa.select([db.Utterance.id, db.Utterance.start_raw, db.Utterance.end_raw])
    rows = conn.execute(s)
    results = []
    for row in rows:
        if row.start_raw: #.isnot(None):
            try:
                start = age.unify_timestamps(row.start_raw)
                end = age.unify_timestamps(row.end_raw)
                results.append({'utterance_id': row.id, 'start': start, 'end': end})
            except Exception as e:
                logger.warning('Error unifying timestamps: {}'.format(row, e), exc_info=sys.exc_info())
    rows.close()
    _update_rows(db.Utterance.__table__, 'utterance_id', results)


def _utterances_replace_morphemes():
    """ TODO: talk to Robert; remove if not needed. """
    s = sa.select([db.Utterance.id,
                   db.Utterance.corpus,
                   db.Utterance.morpheme,
                   db.Utterance.gloss_raw,
                   db.Utterance.pos_raw,
                   db.Utterance.utterance_raw,
                   db.Utterance.translation]).where(sa.or_(
        db.Utterance.corpus=="Chintang",
        db.Utterance.corpus=="Russian",
        db.Utterance.corpus=="Indonesian"))
    rows = conn.execute(s)
    results = []

    for row in rows:
        if row.corpus == "Chintang":
            morpheme = None if row.morpheme is None else re.sub('\*\*\*', '???', row.morpheme)
            gloss_raw = None if row.gloss_raw is None else re.sub('\*\*\*', '???', row.gloss_raw)
            pos_raw = None if row.pos_raw is None else re.sub('\*\*\*', '???', row.pos_raw)
            results.append({'utterance_id': row.id, 'morpheme': morpheme, 'gloss_raw': gloss_raw, 'pos_raw': pos_raw, 'utterance_raw': row.utterance_raw, 'translation': row.translation})

        if row.corpus == "Russian":
            morpheme = None if row.morpheme is None else re.sub('xxx?|www', '???', row.morpheme)
            results.append({'utterance_id': row.id, 'morpheme': morpheme, 'gloss_raw': row.gloss_raw, 'pos_raw': row.pos_raw, 'utterance_raw': row.utterance_raw, 'translation': row.translation})

        if row.corpus == "Indonesian":
            morpheme = None if row.morpheme is None else re.sub('xxx?|www', '???', row.morpheme)
            gloss_raw = None if row.gloss_raw is None else re.sub('xxx?|www', '???', row.gloss_raw)
            utterance_raw = None if row.utterance_raw is None else re.sub('xxx?|www', '???', row.utterance_raw)
            translation = None if row.translation is None else re.sub('xxx?|www', '???', row.translation)
            pos_raw = None if row.pos_raw is None else re.sub('\*\*\*', '???', row.pos_raw)
            results.append({'utterance_id': row.id, 'morpheme': morpheme, 'gloss_raw': gloss_raw, 'pos_raw': pos_raw, 'utterance_raw': utterance_raw, 'translation': translation})

    rows.close()
    _update_rows(db.Utterance.__table__, 'utterance_id', results)


def _utterances_change_indonesian_speaker_labels():
    s = sa.select([db.Utterance.id, db.Utterance.speaker_label]).where(db.Utterance.corpus == "Indonesian")
    rows = conn.execute(s)
    results = []
    for row in rows:
        if row.speaker_label:
            if not 'EXP' in row.speaker_label:
                results.append({'utterance_id': row.id, 'speaker_label': row.speaker_label[0:3]})
            else:
                results.append({'utterance_id': row.id, 'speaker_label': row.speaker_label[3:]})
    rows.close()
    _update_rows(db.Utterance.__table__, 'utterance_id', results)


def _utterances_get_uniquespeaker_ids():
    """ Add speaker ids and unique speaker ids to utterances table. """

    rows = engine.execute('''
    select u.id, u.speaker_label, u.session_id_fk, u.corpus, s.id as speaker_id, s.uniquespeaker_id_fk
    from utterances u
    left join speakers s
    on u.speaker_label = s.speaker_label
    and u.session_id_fk = s.session_id_fk
    and u.corpus = s.corpus''')

    results = []
    for row in rows:
        if row.speaker_label:
            results.append({'utterance_id': row.id, 'uniquespeaker_id_fk': row.uniquespeaker_id_fk, 'speaker_id_fk': row.speaker_id})
    rows.close()
    _update_rows(db.Utterance.__table__, 'utterance_id', results)


def _utterances_get_directedness():
    """ Infer child directedness for each utterance. Skips Chintang. """

    rows = engine.execute('''
        select u.id, u.corpus, u.addressee, u.speaker_label, s.macrorole 
        from utterances u
        left join speakers s
        on u.addressee = s.speaker_label
        and u.session_id_fk = s.session_id_fk
        where u.corpus != "Chintang"''')

    results = []
    for row in rows:
        if row.addressee:
            if row.macrorole == 'Target_Child' and row.speaker_label != row.addressee:
                results.append({'utterance_id': row.id, 'childdirected': 1})
            else:
                results.append({'utterance_id': row.id, 'childdirected': 0})
        else:
            results.append({'utterance_id': row.id, 'childdirected': 0})
    rows.close()
    _update_rows(db.Utterance.__table__, 'utterance_id', results)


def process_morphemes_table():
    """ Post-process the morphemes table.
    """
    print("_morphemes_infer_pos_chintang")
    _morphemes_infer_pos_chintang()

    print("_morphemes_infer_pos_indonesian")
    _morphemes_infer_pos_indonesian()

    print("_morphemes_infer_pos")
    _morphemes_infer_pos()

    print("_morphemes_infer_labels")
    _morphemes_infer_labels()

    print("_morphemes_unify_label")
    _morphemes_unify_label()

    print("_morphemes_get_pos_index")
    _morphemes_get_pos_index()


def _morphemes_infer_pos_chintang():
    """ Chintang part-of-speech inference. Also removes hyphens from raw input data. """
    s = sa.select([db.Morpheme.id, db.Morpheme.corpus, db.Morpheme.pos_raw]).where(db.Morpheme.corpus == "Chintang")
    rows = conn.execute(s)
    results = []
    for row in rows:
        if row.pos_raw:
            if row.pos_raw.startswith('-'):
                results.append({'morpheme_id': row.id, 'pos_raw': "sfx"})
            elif row.pos_raw.endswith('-'):
                results.append({'morpheme_id': row.id, 'pos_raw': "pfx"})
    rows.close()
    _update_rows(db.Morpheme.__table__, 'morpheme_id', results)


def _morphemes_infer_pos_indonesian():
    """ Indonesian part-of-speech inference. Clean up affix markers "-"; assign sfx, pfx, stem. """
    s = sa.select([db.Morpheme.id, db.Morpheme.corpus, db.Morpheme.gloss_raw, db.Morpheme.pos_raw]).where(db.Morpheme.corpus == "Indonesian")
    rows = conn.execute(s)
    results = []
    for row in rows:
        if row.gloss_raw:
            if row.gloss_raw.startswith('-'):
                results.append({'morpheme_id': row.id, 'pos_raw': "sfx"})
            elif row.gloss_raw.endswith('-'):
                results.append({'morpheme_id': row.id, 'pos_raw': "pfx"})
            elif row.gloss_raw == '???':
                results.append({'morpheme_id': row.id, 'pos_raw': "???"})
            else:
                if row.pos_raw not in {'sfx', 'pfx', '???'}:
                    results.append({'morpheme_id': row.id, 'pos_raw': "stem"})
    rows.close()
    _update_rows(db.Morpheme.__table__, 'morpheme_id', results)


def _morphemes_infer_pos():
    """ Part-of-speech inference. Clean up affix markers "-"; assign sfx, pfx, stem.
    """
    s = sa.select([db.Morpheme.id, db.Morpheme.corpus, db.Morpheme.morpheme, db.Morpheme.gloss_raw, db.Morpheme.pos_raw]).where(sa.or_(
        db.Morpheme.corpus == "Indonesian",
        db.Morpheme.corpus == "Chintang"))
    rows = conn.execute(s)
    results = []
    for row in rows:
        morpheme = None if row.morpheme is None else row.morpheme.replace('-', '')
        gloss_raw = None if row.gloss_raw is None else row.gloss_raw.replace('-', '')
        pos_raw = None if row.pos_raw is None else row.pos_raw.replace('-', '')
        results.append({'morpheme_id': row.id, 'pos_raw': pos_raw, 'gloss_raw': gloss_raw, 'morpheme': morpheme})
    rows.close()
    _update_rows(db.Morpheme.__table__, 'morpheme_id', results)


def _morphemes_infer_labels():
    """ Indonesian, Japanese_MiiPro, Japanese_Miyata, Sesotho, Turkish have morpheme or pos substitutions in their config files. """
    s = sa.select([db.Morpheme.id, db.Morpheme.corpus, db.Morpheme.gloss_raw, db.Morpheme.pos, db.Morpheme.morpheme])
    query = conn.execute(s)
    results = []
    for corpus, rows in groupby(query, lambda r: r[1]):
        config = get_config(corpus)
        if config['morphemes']['substitutions'] == 'yes':
            target_tier = config['morphemes']['target_tier']
            substitutions = config['substitutions']
            for row in rows:
                result = None if row.gloss_raw not in substitutions else substitutions[row.gloss_raw]
                if result:
                    if target_tier == "morpheme":
                        results.append({'morpheme_id': row.id, 'morpheme': result, 'pos': row.pos})
                    if target_tier == "pos":
                        results.append({'morpheme_id': row.id, 'morpheme': row.morpheme, 'pos': result})
    query.close()
    _update_rows(db.Morpheme.__table__, 'morpheme_id', results)


def _morphemes_unify_label():
    """ Key-value substitutions for morphological glosses and parts-of-speech in the database. If no key is
        defined in the corpus ini file, then None (NULL) is written to the database.
    """
    # TODO: Insert some debugging here if the labels are missing?
    s = sa.select([db.Morpheme.id, db.Morpheme.corpus, db.Morpheme.gloss_raw, db.Morpheme.pos_raw])
    query = conn.execute(s)
    results = []
    for corpus, rows in groupby(query, lambda r: r[1]):
        config = get_config(corpus)
        glosses = config['gloss']
        poses = config['pos']
        for row in rows:
            gloss = None if row.gloss_raw not in glosses else glosses[row.gloss_raw]
            pos = None if row.pos_raw not in poses else poses[row.pos_raw]
            results.append({'morpheme_id': row.id, 'gloss': gloss, 'pos': pos})
    query.close()
    _update_rows(db.Morpheme.__table__, 'morpheme_id', results)


def _morphemes_get_pos_index():
    """ Infer the word's part-of-speech from the morphemes table as index for word pos assignment. """
    s = sa.select([db.Morpheme.id, db.Morpheme.pos, db.Morpheme.word_id_fk])
    rows = conn.execute(s)
    for row in rows:
        if not row.pos in ["sfx", "pfx"]:
            # row.id will be int type in other tables when look up occurs; type it int here for convenience
            try:
                pos_index[int(row.word_id_fk)] = row.pos
            except TypeError:
                pass
    rows.close()


def process_words_table():
    """ Add POS labels to the word table. """
    s = sa.select([db.Word.id])
    rows = conn.execute(s)
    results = []
    for row in rows:
        if row.id in pos_index:
            results.append({'word_id': row.id, 'pos': pos_index[row.id]})
    rows.close()
    _update_rows(db.Word.__table__, 'word_id', results)


### Util functions ###
def _update_rows(t, binder, rows):
    """ Update rows for a given table, bindparameter and list of dictionaries contain column-value mappings. """
    stmt = t.update().where(t.c.id == sa.bindparam(binder)).values()
    try:
        conn.execute(stmt, rows)
    except sa.exc.StatementError:
        pass


def _insert_rows(t, rows):
    """ Insert rows for a given table, bindparameter and list of dictionaries contain column-value mappings. """
    stmt = t.insert().values()
    try:
        conn.execute(stmt, rows)
    except sa.exc.IntegrityError:
        pass


def _update_imdi_age(rows):
    """ Process speaker ages in IMDI corpora.

    Finds all the recording sessions in the corpus in the config, then, for each speaker
    in the session:

    First attempts to calculate ages from the speaker's birth date and the session's
    recording date. For speakers where this fails, looks for speakers that already
    have a properly formatted age, transfers this age from the age_raw column to the
    age column and calculates age_in_days from it.

    Finally, it looks for speakers that only have an age in years and does the same.
    """

    # TODO: does this actually do anything in the old code?
    # if row.birthdate is None:
    #    return

    results = []
    for row in rows:
        if "Un" not in row.birthdate and "None" not in row.birthdate:
            try:
                session_date = _get_session_date(row.session_id_fk)
                recording_date = age.numerize_date(session_date)
                birth_date = age.numerize_date(row.birthdate)
                ages = age.format_imdi_age(birth_date, recording_date)
                formatted_age = ages[0]
                age_in_days = ages[1]
                results.append({'speaker_id': row.id, 'age': formatted_age, 'age_in_days': age_in_days})
            except age.BirthdateError as e:
                logger.warning('Couldn\'t calculate age of speaker {} from birth and recording dates: '
                               'Invalid birthdate.'.format(row.id), exc_info=sys.exc_info())
            except age.SessionDateError as e:
                logger.warning('Couldn\'t calculate age of speaker {} from birth and recording dates: '
                               'Invalid recording date.'.format(row.id), exc_info=sys.exc_info())

        if re.fullmatch(age_pattern, row.age_raw):
            formatted_age = row.age_raw
            age_in_days = age.calculate_xml_days(row.age_raw)
            results.append({'speaker_id': row.id, 'age': formatted_age, 'age_in_days': age_in_days})

        if "None" not in row.age_raw or "Un" not in row.age_raw or row.age is None:
            if not cleaned_age.fullmatch(row.age_raw):
                try:
                    ages = age.clean_incomplete_ages(row.age_raw)
                    formatted_age = ages[0]
                    age_in_days = ages[1]
                    results.append({'speaker_id': row.id, 'age': formatted_age, 'age_in_days': age_in_days})
                except ValueError as e:
                    logger.warning('Couldn\'t transform age of speaker {}'.format(row.id), exc_info=sys.exc_info())
    return results


def _update_xml_age(rows):
    """ Process speaker ages in Chat XML corpora.

    Finds all speakers from the corpus in the config and calls methods from age.py to
    fill in the age and age_in_days columns.
    """
    results = []
    for row in rows:
        if row.age_raw:
            new_age = age.format_xml_age(row.age_raw)
            if new_age:
                aid = age.calculate_xml_days(new_age)
                results.append({'speaker_id': row.id, 'age': new_age, 'age_in_days': aid})
    return results


def _get_session_date(session_id):
    """ Return the session date from the session table. """
    s = sa.select([db.Session]).where(db.Session.id == session_id)
    row = conn.execute(s).fetchone()
    return row.date


if __name__ == "__main__":
    import time
    import argparse

    start_time = time.time()

    p = argparse.ArgumentParser()
    p.add_argument('-t', action='store_true')
    p.add_argument('-s', action='store_true')
    args = p.parse_args()

    global logger
    logger = logging.getLogger('pipeline.postprocessor')
    handler = logging.FileHandler('errors.log', mode='a')
    handler.setLevel(logging.INFO)
    if args.s:
        formatter = logging.Formatter('%(asctime)s - %(name)s - '
                                        '%(levelname)s - %(message)s')
    else:
        formatter = pipeline_logging.SuppressingFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    main(args)

    print("%s seconds --- Finished" % (time.time() - start_time))
    print()
    print('Next, run tests:')
    print('python3 -m "nose" -s -w tests test_regression.py')
    print('python3 -m "nose" -s -w tests test_integrity.py:ValidationTest_DevDB')
