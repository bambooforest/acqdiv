from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='acqdiv',

    #Using semver
    version='1.0.0',

    description='The ACQDIV corpus pipeline',
    long_description=long_description,

    url='https://github.com/uzling/acqdiv',

    author='The ACQDIV team',
    author_email='robert.schikowski@uzh.ch',

    license='custom',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',

        'Intended Audience :: Other Audience',
        'Topic :: Text Processing :: Linguistic',

        'License :: Other/Proprietary License',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],

    keywords='data linguistics',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=['pipeline', 'pyacqdiv'],

    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': ['acqdiv=pyacqdiv.scripts.cli:main'],
    },
    tests_require=[],
    test_suite="acqdiv"
)
