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
    executable_name = "log_extended.cmd - Shortcut.lnk"
    target_name = "Merged.etl"

    for filename in glob(os.path.join(traces_base_path, "*.etl")):
        os.remove(filename)

    proc = psutil.Popen(os.path.join(traces_base_path, executable_name), stdout=PIPE, stderr=PIPE, shell=True)

    proc.communicate()

    sleep(5)

    with zipfile.ZipFile(os.path.join(archive_path, archive_name), "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(os.path.join(traces_base_path, target_name), arcname=target_name)
