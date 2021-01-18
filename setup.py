from setuptools import setup, find_packages

setup(name='taky',
    python_requires='>=3.6',
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    description='TAK Server',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'taky = taky.__main__:main'
        ]
    }
)
