from distutils.core import setup
import py2exe

setup(console=[
        {
            "script": 'flexsoap.py',
            "dest_base": "flexsoap"
        }],
    options={
        "py2exe":
        {
            "bundle_files": 2,
            "compressed": True,
            "optimize": 1,
            "packages": ['lxml', 'bs4', 'requests_kerberos']
        }
    },
    zipfile=None

)
