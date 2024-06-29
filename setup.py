from setuptools import Extension, setup

COMPILE_ARGS = ["-O2"]


setup(
    ext_modules=[
        # Extension(
        #     "lilya.apps",
        #     ["lilya/apps.c"],
        #     extra_compile_args=COMPILE_ARGS,
        # ),
        Extension(
            "lilya.exceptions",
            ["lilya/exceptions.c"],
            extra_compile_args=COMPILE_ARGS,
        ),
        # Extension(
        #     "lilya.background",
        #     ["lilya/background.c"],
        #     extra_compile_args=COMPILE_ARGS,
        # ),
        # Extension(
        #     "lilya.concurrency",
        #     ["lilya/concurrency.c"],
        #     extra_compile_args=COMPILE_ARGS,
        # ),
        # Extension(
        #     "lilya.context",
        #     ["lilya/context.c"],
        #     extra_compile_args=COMPILE_ARGS,
        # ),
        # Extension(
        #     "lilya.controllers",
        #     ["lilya/controllers.c"],
        #     extra_compile_args=COMPILE_ARGS,
        # ),
        # Extension(
        #     "lilya.exceptions",
        #     ["lilya/exceptions.c"],
        #     extra_compile_args=COMPILE_ARGS,
        # ),
        # Extension(
        #     "lilya.datastructures",
        #     ["lilya/datastructures.c"],
        #     extra_compile_args=COMPILE_ARGS,
        # ),
        # Extension(
        #     "lilya.encoders",
        #     ["lilya/encoders.c"],
        #     extra_compile_args=COMPILE_ARGS,
        # ),
        # Extension(
        #     "lilya.requests",
        #     ["lilya/requests.c"],
        #     extra_compile_args=COMPILE_ARGS,
        # ),
        # Extension(
        #     "lilya.responses",
        #     ["lilya/responses.c"],
        #     extra_compile_args=COMPILE_ARGS,
        # ),
        # Extension(
        #     "lilya.routing",
        #     ["lilya/routing.c"],
        #     extra_compile_args=COMPILE_ARGS,
        # ),
        # Extension(
        #     "lilya.transformers",
        #     ["lilya/transformers.c"],
        #     extra_compile_args=COMPILE_ARGS,
        # ),
        # Extension(
        #     "lilya.websockets",
        #     ["lilya/websockets.c"],
        #     extra_compile_args=COMPILE_ARGS,
        # ),
    ]
)
