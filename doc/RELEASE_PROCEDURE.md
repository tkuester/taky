1. Update changelog, compare with `git lg`
2. Confirm all issues closed on github
3. Ensure all documentation updated with new features
4. Run `pylint -d R,C,W` to look for errors
5. Run `pyright` and look for anything critical
6. Run `python3 -m unittest` and look for failures
7. `git diff` the previous tag, and audit the line-by-line changes
8. `python3 ./setup.py sdist`, and upload to TestPyPI
9. Test install the server from TestPyPI, and run an integration test
	a. Setup taky for a system wide install
	b. Build a client certificate, and install on EUD
	c. Connect to the server
	d. Observe user connection with `takyctl status`
	e. Build a sample data package, and upload to the server
	f. Delete the datapackage from the EUD
	g. Search the server for the datapackage, and download it
10. Push all commits and tags to github, prune old branches
11. Upload to PyPI with twine
12. Make release announcement on discord
