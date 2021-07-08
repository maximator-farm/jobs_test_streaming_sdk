import sys
import json
import os
import argparse
from statistics import median

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir)
        )
    )


def get_framerate(keys):
    if '-Framerate' in keys:
        return int(keys.split('-Framerate')[1].split()[0])
    else:
        return 30


def parse_block_line(args, line, saved_values, framerate):
    if 'Average latency' in line:
        # Line example:
        # 2021-05-31 09:01:55.469     3F90 [RemoteGamePipeline]    Info: Average latency: full 35.08, client  1.69, server 21.83, encoder  3.42, network 11.56, decoder  1.26, Rx rate: 122.67 fps, Tx rate: 62.33 fps
        if 'client_latencies' not in saved_values:
            saved_values['client_latencies'] = []

        encoder_value = float(line.split('client')[1].split(',')[0])
        saved_values['client_latencies'].append(encoder_value)

        if 'server_latencies' not in saved_values:
            saved_values['server_latencies'] = []

        encoder_value = float(line.split('server')[1].split(',')[0])
        saved_values['server_latencies'].append(encoder_value)

        if 'network_latencies' not in saved_values:
            saved_values['network_latencies'] = []

        network_latencies = float(line.split('network')[1].split(',')[0])
        saved_values['network_latencies'].append(network_latencies)  

        if 'encoder_values' not in saved_values:
            saved_values['encoder_values'] = []

        encoder_value = float(line.split('encoder')[1].split(',')[0])
        saved_values['encoder_values'].append(encoder_value)

        if 'decoder_values' not in saved_values:
            saved_values['decoder_values'] = []

        encoder_value = float(line.split('decoder')[1].split(',')[0])
        saved_values['decoder_values'].append(encoder_value)      

        if 'rx_rates' not in saved_values:
            saved_values['rx_rates'] = []

        encoder_value = float(line.split('Rx rate:')[1].split(',')[0].replace('fps', ''))
        saved_values['rx_rates'].append(encoder_value)

        if 'tx_rates' not in saved_values:
            saved_values['tx_rates'] = []

        encoder_value = float(line.split('Tx rate:')[1].split(',')[0].replace('fps', ''))
        saved_values['tx_rates'].append(encoder_value)

    elif 'Queue depth' in line:
        # Line example:
        # 2021-07-07 13:43:17.038      A60 [RemoteGamePipeline]    Info: Queue depth: Encoder: 0, Decoder: 0
        if 'queue_encoder_values' not in saved_values:
            saved_values['queue_encoder_values'] = []

        queue_encoder_value = float(line.split('Encoder:')[1].split(',')[0])
        saved_values['queue_encoder_values'].append(queue_encoder_value)

        if 'queue_decoder_values' not in saved_values:
            saved_values['queue_decoder_values'] = []

        queue_encoder_value = float(line.split('Decoder:')[1].split(',')[0])
        saved_values['queue_decoder_values'].append(queue_encoder_value)

    elif 'A/V desync' in line:
        # Line example:
        # 2021-07-07 13:43:23.081      A60 [RemoteGamePipeline]    Info: A/V desync:  1.29 ms, video bitrate: 20.00 Mbps
        if 'decyns_values' not in saved_values:
            saved_values['decyns_values'] = []

        decyns_values = float(line.split('desync:')[1].split(',')[0].replace('ms', ''))
        saved_values['decyns_values'].append(decyns_values)

        if 'video_bitrate' not in saved_values:
            saved_values['video_bitrate'] = []

        video_bitrate = float(line.split('video bitrate:')[1].replace('Mbps', ''))
        saved_values['video_bitrate'].append(video_bitrate)

    elif 'Average bandwidth' in line:
        # Line example:
        # 2021-07-07 13:43:32.160      A60 [RemoteGamePipeline]    Info: Average bandwidth: Tx: 16794.37 kbps (video/audio/user: 16255.78/139.55/ 0.00), Rx: 147.09 kbps (ctrl/audio/user: 147.09/ 0.00/ 0.00)
        if 'average_bandwidth_tx' not in saved_values:
            saved_values['average_bandwidth_tx'] = []

        average_bandwidth_tx = float(line.split('Tx:')[1].split('kbps')[0])
        saved_values['average_bandwidth_tx'].append(average_bandwidth_tx)

    elif 'Send time (avg/worst)' in line:
        # Line example:
        # 2021-07-07 13:43:23.082      A60 [RemoteGamePipeline]    Info: Send time (avg/worst):  0.05/ 5.95 ms
        if 'send_time_avg' not in saved_values:
            saved_values['send_time_avg'] = []

        send_time_avg = float(line.split('(avg/worst):')[1].split('/')[0])
        saved_values['send_time_avg'].append(send_time_avg)

        if 'send_time_worst' not in saved_values:
            saved_values['send_time_worst'] = []

        send_time_worst = float(line.split('/')[2].replace('ms', ''))
        saved_values['send_time_worst'].append(send_time_worst)


def save_error(args, line, saved_errors):
    error_message = line.split(":", maxsplit = 3)[3].strip().split('.')[0]

    if error_message not in saved_errors:
        saved_errors.append(error_message)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--work_dir', required=True)
    parser.add_argument('--execution_type', required=True)
    args = parser.parse_args()
    work_dir = args.work_dir

    json_files = list(
        filter(
            lambda x: x.endswith('RPR.json'), os.listdir(work_dir)
        )
    )

    reports = []

    for file in json_files:
        json_content = json.load(open(os.path.join(work_dir, file), 'r'))[0]

        if json_content.get('group_timeout_exceeded', False):
            json_content['message'].append('Test group timeout exceeded')

        log_key = '{}_log'.format(args.execution_type)

        block_number = 0
        saved_values = {}
        results = {}
        saved_errors = []

        end_of_block = False

        log_path = os.path.join(work_dir, json_content[log_key]).replace('/', os.path.sep).replace('\\', os.path.sep)

        if log_key in json_content and os.path.exists(log_path):
            framerate = get_framerate(json_content["keys"])

            with open(log_path, 'r') as log_file:
                log = log_file.readlines()
                for line in log:
                    # beginning of the new block
                    if 'Average latency' in line:
                        end_of_block = False
                        block_number += 1

                    # skip three first blocks of output with latency (it can contains abnormal data due to starting of Streaming SDK)
                    if block_number > 3:
                        if not end_of_block:
                            parse_block_line(args, line, saved_values, framerate)
                        elif line.strip():
                            save_error(args, line, saved_errors)

                    if 'Queue depth' in line:
                        end_of_block = True

        reports.append(json_content)
        print(saved_errors)

    with open(os.path.join(work_dir, 'report_compare.json'), 'w') as f: json.dump(reports, f, indent=4)
