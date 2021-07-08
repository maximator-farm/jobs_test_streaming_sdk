import sys
import json
import os
import argparse
from statistics import stdev

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


def parse_block_line(args, line, saved_values):
    if 'Average latency' in line:
        # Line example:
        # 2021-05-31 09:01:55.469     3F90 [RemoteGamePipeline]    Info: Average latency: full 35.08, client  1.69, server 21.83, encoder  3.42, network 11.56, decoder  1.26, Rx rate: 122.67 fps, Tx rate: 62.33 fps
        if 'client' in line:
            if 'client_latencies' not in saved_values:
                saved_values['client_latencies'] = []

            client_latency = float(line.split('client')[1].split(',')[0])
            saved_values['client_latencies'].append(client_latency)

        if 'server' in line:
            if 'server_latencies' not in saved_values:
                saved_values['server_latencies'] = []

            server_latency = float(line.split('server')[1].split(',')[0])
            saved_values['server_latencies'].append(server_latency)

        if 'network' in line:
            if 'network_latencies' not in saved_values:
                saved_values['network_latencies'] = []

            network_latency = float(line.split('network')[1].split(',')[0])
            saved_values['network_latencies'].append(network_latency)  

        if 'encoder' in line:
            if 'encoder_values' not in saved_values:
                saved_values['encoder_values'] = []

            encoder_value = float(line.split('encoder')[1].split(',')[0])
            saved_values['encoder_values'].append(encoder_value)

        if 'decoder' in line:
            if 'decoder_values' not in saved_values:
                saved_values['decoder_values'] = []

            decoder_value = float(line.split('decoder')[1].split(',')[0])
            saved_values['decoder_values'].append(decoder_value)      

        if 'Rx rate:' in line:
            if 'rx_rates' not in saved_values:
                saved_values['rx_rates'] = []

            rx_rate = float(line.split('Rx rate:')[1].split(',')[0].replace('fps', ''))
            saved_values['rx_rates'].append(rx_rate)

        if 'Tx rate:' in line:
            if 'tx_rates' not in saved_values:
                saved_values['tx_rates'] = []

            tx_rate = float(line.split('Tx rate:')[1].split(',')[0].replace('fps', ''))
            saved_values['tx_rates'].append(tx_rates)

    elif 'Queue depth' in line:
        # Line example:
        # 2021-07-07 13:43:17.038      A60 [RemoteGamePipeline]    Info: Queue depth: Encoder: 0, Decoder: 0
        if 'queue_encoder_values' not in saved_values:
            saved_values['queue_encoder_values'] = []

        queue_encoder_value = float(line.split('Encoder:')[1].split(',')[0])
        saved_values['queue_encoder_values'].append(queue_encoder_value)

        if 'queue_decoder_values' not in saved_values:
            saved_values['queue_decoder_values'] = []

        queue_decoder_value = float(line.split('Decoder:')[1].split(',')[0])
        saved_values['queue_decoder_values'].append(queue_decoder_value)

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


def parse_error(args, line, saved_errors):
    error_message = line.split(":", maxsplit = 3)[3].strip().split('.')[0]

    if error_message not in saved_errors:
        saved_errors.append(error_message)


def update_status(args, json_content, saved_values, saved_errors, framerate):
    # TODO - rework rule №1
    # rule №1: encoder >= framerate -> problem with app
    if 'encoder_values' in saved_values:
        for encoder_value in saved_values['encoder_values']:
            if encoder_value >= framerate:
                json_content["message"].append("Application problem: Encoder is equal to or bigger than framerate")
                if json_content["test_status"] != "error":
                    json_content["test_status"] = "failure"

                break

    # rule №2.1: tx rate - rx rate > 3 -> problem with network
    if 'rx_rates' in saved_values and 'tx_rates' in saved_values:
        for i in range(len(saved_values['rx_rates'])):
            if saved_values['rx_rates'][i] - saved_values['tx_rates'][i] > 3:
                json_content["message"].append("Network problem: TX Rate is much bigger than Rx Rate")

                break

    # rule №2.2: framerate - tx rate > 4 -> problem with app
    if 'tx_rates' in saved_values:
        for tx_rate in saved_values['tx_rates']:
            if framerate - tx_rate > 4:
                json_content["message"].append("Application problem: TX Rate is much less than framerate")

                break

    # rule №4: TODO - implement

    # rule №6.1: client latency <= decoder -> issue with app
    if 'client_latencies' in saved_values and 'decoder_values' in saved_values:
        for i in range(len(saved_values['client_latencies'])):
            if saved_values['client_latencies'][i] <= saved_values['decoder_values'][i]:
                json_content["message"].append("Application problem: client latency is less than decoder value")
                if json_content["test_status"] != "error":
                    json_content["test_status"] = "failure"

                break

    # rule №6.2: server latency <= encoder -> issue with app
    if 'server_latencies' in saved_values and 'encoder_value' in saved_values:
        for i in range(len(saved_values['server_latencies'])):
            if saved_values['server_latencies'][i] <= saved_values['encoder_value'][i]:
                json_content["message"].append("Application problem: server latency is less than encoder value")
                if json_content["test_status"] != "error":
                    json_content["test_status"] = "failure"

                break

    # rule №7: |decyns value| > 100ms -> issue with app
    if 'decyns_values' in saved_values:
        for decyns_value in saved_values['decyns_values']:
            if abs(decyns_value) > 100:
                json_content["message"].append("Application problem: Absolute value of A/V desync is more than 100 ms")

                break

    # rule №8: TODO - implement

    # rule №9: TODO - implement

    # rule №10: send time avg * 100 > send time worst -> issue with network
    if 'send_time_avg' in saved_values and 'send_time_worst' in saved_values:
        for i in range(len(saved_values['send_time_avg'])):
            if saved_values['send_time_avg'][i] * 100 > saved_values['send_time_worst'][i]:
                json_content["message"].append("Network problem: average send time is 100 times more than the worst send time")

                break

    # rule №11: TODO - implement


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

        if args.execution_type == "server":
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
                                parse_block_line(args, line, saved_values)
                            elif line.strip():
                                parse_error(args, line, saved_errors)

                        if 'Queue depth' in line:
                            end_of_block = True

                    update_status(args, json_content, saved_values, saved_errors, framerate)

        reports.append(json_content)

    with open(os.path.join(work_dir, 'report_compare.json'), 'w') as f: json.dump(reports, f, indent=4)
