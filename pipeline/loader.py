""" Entry point for loading acqdiv corpora into the database
"""

from processors import *
from postprocessor import *
from parsers import *
from database_backend import *
import time

# TODO: setup the config files, e.g. Chintang.ini, Cree.ini...
#  - define the corpus/session-specific attributes in each config; see example in Chintang
#  - integrate metadata stuff

if __name__ == "__main__":
    start_time = time.time()

    # Initialize database connection and drop and then create tables on each call.
    # http://docs.sqlalchemy.org/en/latest/orm/session_basics.html#session-faq-whentocreate
    engine = db_connect()
    create_tables(engine)

    configs = ['Chintang.ini', 'Cree.ini', 'Indonesian.ini', 'Inuktitut.ini', 'Japanese_Miyata.ini',
              'Japanese_MiiPro.ini', 'Russian.ini', 'Sesotho.ini', 'Turkish.ini', 'Yucatec.ini']

    # configs = ['Chintang.ini']
    # configs = ['Cree.ini']
    # configs = ['Indonesian.ini']
    # configs = ['Inuktitut.ini']
    # configs = ['Japanese_MiiPro.ini'] # fails
    # configs = ['Japanese_Miyata.ini']
    # configs = ['Russian.ini'] # missing metdata data; fails
    # configs = ['Sesotho.ini'] # fails on warnings hixa.json...
    # configs = ['Turkish.ini'] # fails on utterance_cleaned ekin10_30oct01_01-01-10.json
    # configs = ['Yucatec.ini']

    for config in configs:
        # Parse the config file and call the sessions processor
        cfg = CorpusConfigParser()
        cfg.read(config)

        # Process by parsing the files and adding extracted data to the db
        c = CorpusProcessor(cfg, engine)
        c.process_corpus()

        #Do the postprocessing
        print("Postprocessing database entries for {0}...".format(config.split(".")[0]))
        update_age(cfg, engine)
        unify_glosses(cfg, engine)

    print("--- %s seconds ---" % (time.time() - start_time))