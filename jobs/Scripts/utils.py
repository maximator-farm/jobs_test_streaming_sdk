from time import sleep
import psutil
import os
from glob import glob
import zipfile
import psutil
from subprocess import PIPE


def is_case_skipped(case, render_platform):
    if case['status'] == 'skipped':
        return True

    return sum([render_platform & set(x) == set(x) for x in case.get('skip_on', '')])


def close_process(process):
    child_processes = []

    try:
        child_processes = process.children()
    except psutil.NoSuchProcess:
        pass

    for ch in child_processes:
        try:
            ch.terminate()
            sleep(5)
            ch.kill()
            sleep(5)
            status = ch.status()
        except psutil.NoSuchProcess:
            pass

    try:
        process.terminate()
        sleep(5)
        process.kill()
        sleep(5)
        status = process.status()
    except psutil.NoSuchProcess:
        pass


def collect_traces(archive_path, archive_name):
    traces_base_path = "C:\\JN\\GPUViewTraces"
    # traces can generate in gpuview dir
    gpuview_path = os.getenv("GPUVIEW_PATH")
    executable_name = "log_extended.cmd - Shortcut.lnk"
    target_name = "Merged.etl"

    try:
        for filename in glob(os.path.join(traces_base_path, "*.etl")):
            os.remove(filename)
    except Exception:
        pass

    try:
        for filename in glob(os.path.join(gpuview_path, "*.etl")):
            os.remove(filename)
    except Exception:
        pass

    proc = psutil.Popen(os.path.join(traces_base_path, executable_name), stdout=PIPE, stderr=PIPE, shell=True)

    proc.communicate()

    sleep(2)

    target_path = os.path.join(traces_base_path, target_name)

    if not os.path.exists(target_path):
        target_path = os.path.join(gpuview_path, target_name)

        if not os.path.exists(target_path):
            raise Exception("Could not find etl file by path {}".format(target_path))

    with zipfile.ZipFile(os.path.join(archive_path, archive_name), "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(target_path, arcname=target_name)
