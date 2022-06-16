#!/usr/local/bin/python3.7
######################################################################################################################
#
#   Copyright (c) 2022 Newport Electric Boats, LLC. All rights reserved.
#   Electric Vessel Management System (EVMS)
#   Filename: remote.py
#
######################################################################################################################

import os
import socket
import sys
import logging
import subprocess
import boto3
import time

port_v = 49000
port_l = 49001

sw_ver_remote = '0.2.0'

#host_domain = 'aws.newportelectricboats.com'
host_domain = 'ec2-54-151-23-47.us-west-1.compute.amazonaws.com'
release_dir = '/home/neb/evms2/'
backup_dir = '/home/neb/evms2/evms_backup_software/'

#AWS_KEY_ID = 'AKIASFAXZX3IDFWE4S6E' # nate-neb # Account# 148226293456
#AWS_SECRET = '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' # nate-neb #Account# 148226293456
AWS_KEY_ID = 'AKIAYBBSUG4GALZT2KEG' # walt-aws Account #552009479948
AWS_SECRET = '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' # walt-aws Account #552009479948

# Creating Session With Boto3.
session = boto3.Session(
    aws_access_key_id= AWS_KEY_ID,
    aws_secret_access_key=AWS_SECRET
)
# Creating S3 Resource From the Session.
s3 = session.resource('s3')


def update_checksums(dir, filename):
    result = subprocess.run('cd ' + dir + ' && ' + 'sha256sum *', capture_output=True, shell=True)
    file = open(filename, 'w+')
    file.write(result.stdout.decode('utf-8'))
    file.close()


def get_manifest(path, remote_name):
    filenames = []
    list_string = remote_name
    log_list = os.listdir(path)
    for file in log_list:
        if file.endswith('system.log'):
            filenames.append(file)
    for file in filenames:
        list_string += ' ' + file
    return bytes(list_string, 'utf-8')


def version_sync(check):
    update = False
    if not os.path.isfile('system_files.txt'):
        sf = open('system_files.txt', 'x')
        sf.close()
    update_checksums(release_dir, 'system_files.txt')
    logging.basicConfig( format='%(asctime)s - %(message)s', level=logging.INFO, handlers=[
        logging.FileHandler('versionSyncRemote.info'),
        logging.StreamHandler(sys.stdout)
    ])
    logging.info('\n\n     *** *** *** Newport Electric Boats, LLC *** *** *** \nEVMS Software Update System Started: (rev ' + sw_ver_remote + ')\n\nConnecting to server...\n')
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        timeout = 0
        attempt=1
        host = host_domain
        remote_name = socket.gethostname()
        port_open = False
        while not port_open:
            try:
                s.connect((host, port_v))
                port_open = True;
            except Exception as e:
                attempt=attempt+1
                logging.info(".",end="")
                if attempt > 80:
                    attempt = 0
                    logging.info(" ")
                    timeout += 1
                if timeout > 5:
                    logging.info('Server not available. Timeout reached.')
                    return

                continue
        start_message = s.recv(1024)
        if start_message:
            logging.info('Remote '+ remote_name +' connected to aws.NewportElectricBoats.com')
            try:
                logging.info('Remote '+ remote_name +' ----> aws.NewportElectricBoats.com: Uploading system_files.txt\n')
                object = s3.meta.client.upload_file('system_files.txt', 'neblogfiles',
                                                    'System_Files/system_files_'+ remote_name +'.txt')
                s.sendall(bytes(remote_name, 'utf-8'))
            except Exception as e:
                print(e)
                logging.exception(e)
            data = s.recv(1024)
            data = data.decode('utf-8')
            if data:
                objects = s3.Bucket('neblogfiles').objects.filter(Prefix='Update_' + remote_name).all()
                files_in_s3 = [f.key.replace('Update_' + remote_name + '/', '') for f in objects]
                if files_in_s3:
                    if check:
                        return '\n'.join(files_in_s3)
                    update = True
                    logging.info('aws.NewportElectricBoats.com ----> Remote ' + remote_name + ': Downloading Files ' + data + '\n')
                    try:
                        for file in files_in_s3:
                            if file != '':
                                if os.path.isfile(release_dir + file):
                                    if not os.path.isdir(backup_dir):
                                        os.makedirs(backup_dir)
                                    subprocess.run('mv ' + release_dir + file + ' ' + backup_dir + file, shell=True)
                                s3.meta.client.download_file('neblogfiles', 'Update_' + remote_name + '/' + file, '/home/neb/evms/' + file)
                    except Exception as e:
                        logging.error(e)
                    logging.info('aws.NewportElectricBoats.com ----> ' + remote_name + ': Download Finished\n')
            else:
                logging.info('aws.NewportElectricBoats.com ----> ' + remote_name + ': No Updates Needed\n')
            for file in s3.Bucket('neblogfiles').objects.filter(Prefix='Update_' + remote_name).all():
                s3.Object('neblogfiles', file.key).delete()
            update_checksums(release_dir, 'system_files.txt')
    logging.info('Remote ' + remote_name + ' ----> aws.NewportElectricBoats.com: End Connection\n')
    log = logging.getLogger()
    for hdlr in log.handlers[:]:
        log.removeHandler(hdlr)
    return update



def log_sync():
    logging.basicConfig( format='%(asctime)s - %(message)s', level=logging.INFO, handlers=[
        logging.FileHandler('logSyncRemote.info'),
        logging.StreamHandler(sys.stdout)
    ])
    logging.info('\n\n     *** *** *** Newport Electric Boats, LLC *** *** *** \nEVMS Logger Updating System Started: (rev ' + sw_ver_remote + ')\n')
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        host = host_domain
        remote_name = socket.gethostname()
        if not os.path.isdir(release_dir + 'logs'):
            os.makedirs(release_dir + 'logs')
        filenames = get_manifest(release_dir + 'logs', remote_name)
        port_open = False
        while not port_open:
            try:
                s.connect((host, port_l))
                port_open = True;
            except Exception as e:
                continue
        start_message = s.recv(1024)
        if start_message:
            logging.info('Remote '+ remote_name +': connected to aws.NewportElectricBoats.com\n')
            s.sendall(filenames)
            if len(filenames) > 0:
                logging.info('Remote '+ remote_name +' ----> aws.NewportElectricBoats.com: Files Found \n')
                string = '\n'
                for file in str(filenames).split(' ')[1:]:
                    string += file + '\n'
                logging.info(string)
            else:
                logging.info('Remote ' + remote_name + ' ----> aws.newportelectricboats.com: No Files Found \n')
            data = b'0'
            try:
                data = s.recv(1024)
            except Exception as e:
                pass
            data = data.decode('utf-8')
            server_missing_data_list = data.split(' ')
            if server_missing_data_list and data != '0':
                logging.info('aws.NewportElectricBoats.com ----> Remote '+ remote_name +': Files Missing \n')
                string = '\n'
                for file in server_missing_data_list:
                    string += '\t' + file + '\n'
                logging.info(string)
            else:
                logging.info('aws.NewportElectricBoats.com '+ remote_name +' ----> Remote: No Missing Files\n')
            for file in server_missing_data_list:
                if file and file != '0':
                    try:
                        filepath = release_dir + 'logs/' + file
                        logging.info('Remote '+ remote_name +' ----> aws.NewportElectricBoats.com: Uploading ' + file + '\n')
                        s3.meta.client.upload_file(filepath, 'neblogfiles',
                                                   'Logs/'+ remote_name +'/{}'.format(file))
                    except Exception as e:
                        print(e)
                        logging.exception(e)
            logging.info('Remote '+ remote_name +' ----> aws.NewportElectricBoats.com: Upload Finished\n')
    logging.info('Remote '+ remote_name +' ----> aws.NewportElectricBoats.com: End Connection\n')
    log = logging.getLogger()
    for hdlr in log.handlers[:]:
        log.removeHandler(hdlr)

def main():
    logging.info('EVMS sync service: starting up version: ' + sw_ver_remote)
    while True:
        try:
            result = version_sync(False)
            log_sync()
            if result == True:
                subprocess.call(release_dir + 'set_executable.sh')
                time.sleep(10)
                subprocess.call(release_dir + 'reboot.sh')
        except Exception as e:
            logging.info('Exception - main_remote' + str(e))
        logging.info('Sleeping 60 seconds...')
        time.sleep(60)

if __name__ == '__main__':
    main()

