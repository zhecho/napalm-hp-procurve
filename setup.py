"""setup.py file."""

import uuid

from setuptools import setup, find_packages
try:
    from pip._internal.req import parse_requirements
except ImportError:
    from pip.req import parse_requirementsa


__author__ = 'Zhecho Zhechev <zhechev.zhecho@gmail.com>'

install_reqs = parse_requirements('requirements.txt', session=uuid.uuid1())
reqs = [str(ir.req) for ir in install_reqs]

setup(
    name="napalm-hp-procurve",
    version="0.1.0",
    packages=find_packages(),
    author="Zhecho Zhechev",
    author_email="zhechev.zhecho@gmail.com",
    description="Network Automation and Programmability Abstraction Layer with Multivendor support",
    long_description="HP Procurve driver for NAPALM",
    classifiers=[
        'Topic :: Utilities',
         'Programming Language :: Python',
         'Programming Language :: Python :: 3',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS',
    ],
    url="https://github.com/zhecho/napalm-hp-procurve",
    include_package_data=True,
    install_requires=reqs,
)
