#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Title: SAAS - Serveless AWS EBS-snapshot to slack alerts
# Date: 19.01.2019
# Blog: http://101root.blogspot.pe/
# Author: Davis Palomino

import boto3, json, os, datetime, time, datetime, gzip, math
from botocore.vendored import requests

bucketName      =   str(os.environ['bucketName'])
tokenSlack      =   str(os.environ['tokenSlack'])
objectBucket    =   str(os.environ['objectBucket'])
sizeUmbral      =   int(os.environ['sizeUmbral'])
regionAccount   =   str(os.environ['regionAccount'])

instance_id_list=[]
volume_id_list  =[]
snapshot_size   =[]
snapshot_general={}

filejson        ="/tmp/source.json"
ec2 = boto3.resource('ec2', region_name=regionAccount)
alias_client = boto3.client('iam').list_account_aliases()['AccountAliases'][0]
id_client =  boto3.client("sts").get_caller_identity()["Account"]


def slackbot(color,owner,mensaje):
    slack_data = {'channel': "#jarvis-log", 'username': "botjarvis", 'icon_emoji' : ':computer:', "attachments":[{'icon_emoji' : ':computer:',"color":color,"title":owner,"text":mensaje}]}
    requests.post('https://hooks.slack.com/services/{}'.format(tokenSlack), data=json.dumps(slack_data), headers={'Content-Type': 'application/json'})


def sumar_lista(lista):
    suma=0
    for i in lista:
        suma=suma+i
    return (suma)

def lista_volumen():
    for item in ec2.volumes.all():
        volume_id_list.append(item.id)

def lista_instances():
    for item in ec2.instances.all():
        instance_id_list.append(item.id)


def instanceName(idInstance):
    try:
        names_instance=[]
        id_instances = [instance_id['InstanceId'] for instance_id in idInstance]
        for i in id_instances:
            list_name = list(filter(lambda name: name['Key'] == 'Name', (ec2.Instance(i).tags)))
            name_Instance = (list_name[0]['Value'] if ("Name" in str(list_name)) else "Snapshot")
            names_instance.append(str(name_Instance))
        return ", ".join(names_instance)
    except:
        return "Huerfano Instancia"

def volumeName(idVolume,tipoData):
    return ((instanceName(ec2.Volume(idVolume).attachments) if any(ec2.Volume(idVolume).attachments) else "Huerfano Attachment") if (any(idVolume == volume_id for volume_id in volume_id_list)) else "Huerfano Volumen") if tipoData == "InstanceName" else (((ec2.Volume(idVolume).attachments) if any(ec2.Volume(idVolume).attachments) else "Huerfano Attachment") if (any(idVolume == volume_id for volume_id in volume_id_list)) else "Huerfano Volumen")

def uploads3(sourcefile):
    s3 = boto3.resource('s3', region_name=regionAccount)
    s3.Object(bucketName,objectBucket+id_client+"/"+str(time.strftime("%Y/%-m/%-d/"))+time.strftime("%Y%-m%-d%H%m")+'datasource.json').upload_file(Filename=sourcefile)

def generar_json(sourcefile):
    with gzip.GzipFile(sourcefile, 'w') as f:
        json.dump(snapshot_general, f)
    uploads3(sourcefile)

def validarSize(size,numSnapshot):
    if sizeUmbral <= size:
        slackbot("danger","Bot Snapshot "+str(alias_client).upper(), "Se supero el umbral de {}, la cuenta contiene {} con un total de {} snapshot".format(convert_size(int(sizeUmbral)),convert_size(int(size)),numSnapshot))

def convert_size(size_gb):
    if size_gb == 0:
        return "0GB"
    size_name = ("GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_gb, 1024)))
    power = math.pow(1024, i)
    size = round(size_gb / power, 2)
    return "{} {}".format(size, size_name[i])

def lambda_handler(event, context):
    try:
        lista_volumen()
        lista_instances()
        ec2 = boto3.session.Session(region_name = 'us-east-1').client('ec2')
        snapshot_response = ec2.describe_snapshots(OwnerIds=['self'])
        for i in (snapshot_response['Snapshots']):
            i['instanceName'] = str(volumeName(i['VolumeId'],'InstanceName'))
            i['client'] = str(alias_client)
            i['idInstance'] = str(volumeName(i['VolumeId'],'InstanceID'))
            i['StartTime'] = str((i['StartTime'] + datetime.timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S"))
            snapshot_size.append(i['VolumeSize'])
        snapshot_general[str(id_client)]={'snapshot':snapshot_response['Snapshots'],'sizeTotal':sumar_lista(snapshot_size)}
        generar_json(filejson)
        validarSize(int(snapshot_general[id_client]['sizeTotal']),str(len(snapshot_general[id_client]['snapshot'])))
    except IOError as (errno, strerror):
        slackbot("danger","Bot Snapshot", ("Error E/S ({0}): {1}".format(str(errno), str(strerror))))
    except Exception as e:
        slackbot("danger","Bot Snapshot",str(e))