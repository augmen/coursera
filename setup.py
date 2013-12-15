#!/usr/bin/env python

from setuptools import setup
from coursera import _version


# get the requirements from the pip requirements file
requirements = []

with open("requirements.txt") as f:
    for l in f:
        l = l.strip()
        if l:
            requirements.append(l)

setup(name="coursera-dl",
      version=_version.__version__,
      description="Download coursera.org course videos and resources",
      long_description=open("README.md").read(),
      author="Dirk Gorissen",
      author_email="dgorissen@gmail.com",
      url="https://github.com/coursera-dl/coursera",
      license="GPLv3",
      packages=["coursera"],
      entry_points={
          "console_scripts": ["coursera-dl = coursera.coursera:main"]
      },
      install_requires=requirements)
