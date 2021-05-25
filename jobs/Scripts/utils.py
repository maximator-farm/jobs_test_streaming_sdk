from time import sleep


def is_case_skipped(case, render_platform):
    if case['status'] == 'skipped':
        return True
    else:
        return False


def close_process(process):
    child_processes = process.children()
    for ch in child_processes:
        try:
            ch.terminate()
            sleep(2)
            ch.kill()
            sleep(2)
            status = ch.status()
        except:
            pass
