submodule.sync:
	git submodule update --remote --recursive

submodule.init.v19:
	git submodule add -b v19 git@github.com:ti-lekhnath/tistore.git ti-lekhnath/tistore
