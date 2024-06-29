.PHONY: compile


cyt:
	# cython lilya/apps.py
	cython lilya/exceptions.py
	# cython lilya/background.py
	# cython lilya/concurrency.py
	# cython lilya/context.py
	# cython lilya/controllers.py
	# cython lilya/datastructures.py
	# cython lilya/encoders.py
	# cython lilya/requests.py
	# cython lilya/responses.py
	# cython lilya/routing.py
	# cython lilya/transformers.py
	# cython lilya/websockets.py

compile: cyt
	python setup.py build_ext --inplace


clean:
	rm -rf dist/
	rm -rf build/
	rm -f lilya/*.c
	rm -f lilya/*.so


buildext:
	python setup.py build_ext --inplace
