import os
import shlex
import subprocess


def run_cmd(app, cmd, is_app=True):
    env = os.environ.copy()
    if is_app:
        env["LILYA_DEFAULT_APP"] = app
    else:
        env.pop("LILYA_DEFAULT_APP", None)

    process = subprocess.Popen(
        shlex.split(cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    (stdout, stderr) = process.communicate()
    print("\n$ " + cmd)
    print(stdout.decode("utf-8"))
    print(stderr.decode("utf-8"))
    return stdout, stderr, process.wait()
