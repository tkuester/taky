# Developing for Taky

Thanks for considering helping out with development! A few tips on getting
started, to help you work more quickly.

## Environment Setup

If you are developing on a Linux machine, here's a fun quick-and-dirty trick
to get up and running quickly.

```
$ sudo python3 ./setup.py develop
```

This will install symlinks to your taky repository in your global python path.
Any changes you make to the source code will be there the next time you run
or import your code.

## Development Addons

This step is optional, but very helpful for me! I like to run `black` on my
code to keep formating uniform and tidy. I've setup the project with
pre-commit so that this can happen automatically whenever you go to commit.

If you want to set this up, run

```
$ sudo python3 -m pip install -r requirements-dev.txt
$ pre-commit install
```

Now, whenever you commit changes, `pre-commit` will run `black` on your code.
If there are any changes, it will yell at you, and add the changes to staging.
You can check the diff to see what `black` did, add the changes, and then
commit again.

This will save me some time, but is certainly not required! (I'm just happy
to have code coming in!)
