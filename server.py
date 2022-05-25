######################################################################################################################
#
#   Copyright (c) 2022 Newport Electric Boats, LLC. All rights reserved.
#   Electric Vessel Management System (EVMS)
#   Filename: server.py
#
######################################################################################################################
import os
import socket
import sys
import logging
import boto3
import re
import subprocess
from multiprocessing import Process

AWS_KEY_ID = 'AKIASFAXZX3IDFWE4S6E' # nate-neb # Account# 148226293456
AWS_SECRET = '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' # nate-neb #Account# 148226293456
#AWS_KEY_ID = 'AKIAYBBSUG4GALZT2KEG' # walt-aws Account #552009479948
#AWS_SECRET = '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' # walt-aws Account #552009479948
# host = '172.31.29.163' #nate-aws private ip address
host = '172.31.9.204'  # nebServer private ip address


# Creating Session With Boto3.
session = boto3.Session(
    aws_access_key_id= AWS_KEY_ID,
    aws_secret_access_key=AWS_SECRET
)
# Creating S3 Resource From the Session.
s3 = session.resource('s3')

port_v = 49000
port_l = 49001

sw_ver = '0.2.0'

filepath = '/home/ec2-user/nebServer/evms_release_software/'


def update_checksums(dir, filename):
    result = subprocess.run('cd ' + dir + ' && ' + 'sha256sum *', capture_output=True, shell=True)
    file = open(filename, 'w+')
    file.write(result.stdout.decode('utf-8'))
    file.close()


def compare(first_file, second_file):
    files_to_update = []
    first_file_opened = open(first_file, 'r+')
    second_file_opened = open(second_file, 'r+')
    second_file_text = second_file_opened.read()
    for first_file_line in first_file_opened.readlines():
        if first_file_line != '\n':
            sum_and_name = first_file_line.split(' ')
            file_name = sum_and_name[-1].strip()
            first_sum = sum_and_name[0]
            matches = re.findall(first_file_line, second_file_text)
            if not matches:
                files_to_update.append([file_name, first_sum])
    return files_to_update


def version_sync():
    update_checksums('/home/ec2-user/nebServer/evms_release_software', 'system_files.txt')
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port_v))
        while True:
            s.listen()
            conn, addr = s.accept()
            with conn:
                logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO, handlers=[
                    logging.FileHandler('versionSyncServer.info'),
                    logging.StreamHandler(sys.stdout)
                ])
                logging.info('\n\n     *** *** *** Newport Electric Boats, LLC *** *** *** \nEVMS Software Update System (rev ' + sw_ver + ')\n\nIncomming EVMS connection...\n')
                start_message = conn.sendall(b'1')
                data = conn.recv(1024)
                data = data.decode('utf-8')
                if data:
                    try:
                        logging.info('uploading system file list from remote EVMS')
                        s3.meta.client.download_file('neblogfiles', 'System_Files/system_files_'+ data + '.txt',
                                                     'System_Files/system_files_'+ data + '.txt')
                        files_needing_update = compare('system_files.txt', 'System_Files/system_files_'+ data + '.txt')
                        if len(files_needing_update) > 0:
                            logging.info('Server ----> Remote '+ data + ': Updating Files')
                            string = '\n\n'
                            for file in files_needing_update:
                                object = s3.meta.client.upload_file(filepath + file[0],
                                                                    'neblogfiles', 'Update_' + data + '/' + str(file[0]))
                                string += '\t' + file[0] + '\n'
                            logging.info(string)
                            conn.sendall(string.encode())
                            logging.info('Server ----> Remote '+ data + ': Download Finished\n')
                        else:
                            logging.info('Server ----> Remote ' + data + ': No Updates Needed\n')
                    except Exception as e:
                        print(e)
                        logging.exception(e)
            logging.info('Server ----> Remote ' + data + ': End Connection\n')
        log = logging.getLogger()
        for hdlr in log.handlers[:]:
            log.removeHandler(hdlr)


def log_sync():
    missing_from_server = []
    missing_from_server_string = ''
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port_l))
        while True:
            s.listen()
            conn, addr = s.accept()
            with conn:
                logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO, handlers=[
                    logging.FileHandler('logSyncServer.info'),
                    logging.StreamHandler(sys.stdout)
                ])
                logging.info('\n\nNewport Electric Boats: Starting Log Sync Service (rev ' + sw_ver + ')\n')
                logging.info('Server: Beginning Connection\n')
                start_message = conn.sendall(b'1')
                data = conn.recv(1024)
                data = data.decode('utf-8')
                remote_data_list = list(filter(None, data.split(' ')))
                logging.info('Remote ' + remote_data_list[0] + ' ----> Server' + ': Files Found  \n')
                string = '\n'
                for file in remote_data_list[1:]:
                    string += file + '\n'
                logging.info(string)
                server_dir_list = []
                for file in s3.Bucket('neblogfiles').objects.all():
                    server_dir_list.append(file.key.split('/')[-1])
                server_log_list = []
                for file in server_dir_list:
                    if file.endswith('system.log'):
                        server_log_list.append(file)
                for file in remote_data_list:
                    if file not in server_log_list and file.endswith('system.log'):
                        missing_from_server.append(file)
                missing_from_server = list(set(missing_from_server))
                for file in missing_from_server:
                    missing_from_server_string += ' ' + file
                if server_log_list != remote_data_list[1:] and len(missing_from_server) > 0:
                    try:
                        logging.info('Server ----> Remote ' + remote_data_list[0] +': Requesting Files \n')
                        string = '\n'
                        for file in missing_from_server:
                            string += file + '\n'
                        logging.info(string)
                        conn.sendall(bytes(missing_from_server_string, 'utf-8'))
                        logging.info('Server ----> Remote ' + remote_data_list[0] + ': Upload Finished\n')
                    except Exception as e:
                        print(e)
                else:
                    logging.info('Server ----> Remote ' + remote_data_list[0] +': No Missing Files\n')
            logging.info('Server ----> Remote ' + remote_data_list[0] + ': End Connection\n')
        log = logging.getLogger()
        for hdlr in log.handlers[:]:
            log.removeHandler(hdlr)


if __name__ == '__main__':
        try:
            v = Process(target=version_sync)
            l = Process(target=log_sync)
            v.start()
            l.start()
            v.join()
            l.join()
        except Exception as e:
            print(e)
