from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(name='taky',
    python_requires='>=3.7',
    use_scm_version=True,
    author="Tim K",
    author_email="tpkuester@gmail.com",
    setup_requires=['setuptools_scm'],
    install_requires=['lxml', 'dateutils', 'Flask', 'pyopenssl', 'gunicorn'],
    description='A simple TAK server and COT router',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/tkuester/taky',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Topic :: Communications",
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
    ],
    entry_points={
        'console_scripts': [
            'taky = taky.cot.__main__:main',
            'taky_dps = taky.dps.__main__:main',
            'takyctl = taky.__main__:main',
        ]
    }
)
