.PHONY: compile


cyt:
	cython lilya/apps.pyx
	cython lilya/exceptions.pyx
	cython lilya/background.pyx
	cython lilya/concurrency.pyx
	cython lilya/context.pyx
	cython lilya/controllers.pyx
	cython lilya/exceptions.pyx
	cython lilya/datastructures.pyx
	cython lilya/encoders.pyx
	cython lilya/requests.pyx
	cython lilya/responses.pyx
	cython lilya/routing.pyx
	cython lilya/transformers.pyx
	cython lilya/websockets.pyx

compile: cyt
	python3 setup.py build_ext --inplace


clean:
	rm -rf dist/
	rm -rf build/
	rm -f lilya/*.c
	rm -f lilya/*.so


buildext:
	python3 setup.py build_ext --inplace
