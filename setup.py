from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(name='taky',
    python_requires='>=3.6',
    use_scm_version=True,
    author="Tim K",
    author_email="tpkuester@gmail.com",
    setup_requires=['setuptools_scm'],
    install_requires=['lxml', 'dateutils'],
    description='A simple TAK server and COT router',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/tkuester/taky',
    packages=find_packages(),
    classifiers=[
        "Topic :: Communications",
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
    ],
    entry_points={
        'console_scripts': [
            'taky = taky.__main__:main'
        ]
    }
)
