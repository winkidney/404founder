from setuptools import setup, find_packages

install_requires = [
    "requests",
    "pyquery",
]

setup(
    name='tools',
    packages=find_packages("."),
    author='winkidney',
    install_requires=install_requires,
)
