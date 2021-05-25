from time import sleep


def is_case_skipped(case, render_platform):
    if case['status'] == 'skipped':
        return True

    return sum([render_platform & set(x) == set(x) for x in case.get('skip_on', '')])


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
