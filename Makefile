build:
	python scripts/build.py

serve:
	scp -r ./dist/* subhams@studentconf.lids.mit.edu:/home/subhams/studentconf-website-files
