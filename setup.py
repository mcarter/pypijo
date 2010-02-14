from setuptools import setup, find_packages
import os, sys


setup(
    name='pijo',
    version='0.1alpha3',
    author='Michael Carter',
    author_email='CarterMichael@gmail.com',
    url='',
    license='Closed, proprietary',
    description='',
    long_description='',
    packages= find_packages(),
    zip_safe = False,
    install_requires = [ 'concurrence', 'sqlalchemy'],
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],        
)

