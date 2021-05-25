import sys
import json
import os
import argparse

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir)
        )
    )

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--work_dir', required=True)
    args = parser.parse_args()
    wd = args.work_dir

    json_files = list(
        filter(
            lambda x: x.endswith('RPR.json'), os.listdir(wd)
        )
    )

    reports = []

    for file in json_files:
        json_content = json.load(open(os.path.join(wd, file), 'r'))[0]

        if json_content.get('group_timeout_exceeded', False):
            json_content['message'].append('Test group timeout exceeded')

        reports.append(json_content)

    with open(os.path.join(wd, 'report_compare.json'), 'w') as f: json.dump(reports, f, indent=4)
