from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ClientException
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkalidns.request.v20150109.DescribeDomainRecordsRequest import DescribeDomainRecordsRequest
from aliyunsdkalidns.request.v20150109.UpdateDomainRecordRequest import UpdateDomainRecordRequest
from aliyunsdkalidns.request.v20150109 import DescribeDomainRecordInfoRequest
import requests
from requests.exceptions import RequestException
import json
import logging
import logging.handlers
import sys
import time


def get_internet_ip():
    try:
        return requests.get('http://ifconfig.me/ip', timeout=1).text.strip()
    except RequestException as e:
        logger.error(f"Get Internet ip error: {e}")
        return None


def get_dns_ip(client, record_id):
    request = DescribeDomainRecordInfoRequest.DescribeDomainRecordInfoRequest()
    request.set_RecordId(record_id)

    try:
        response = client.do_action_with_exception(request)
    except (ClientException, ServerException) as e:
        logger.error(f"Get DNS ip error: {e}")
        return None

    data = json.loads(str(response, encoding='utf-8'))
    return data["Value"]


def get_record_id(client, domain, record):
    request = DescribeDomainRecordsRequest()
    request.set_accept_format('json')
    request.set_DomainName(domain)

    try:
        response = client.do_action_with_exception(request)
    except (ClientException, ServerException) as e:
        logger.error(f"Get record id error: {e}")
        return None

    json_data = json.loads(str(response, encoding='utf-8'))
    for RecordId in json_data['DomainRecords']['Record']:
        if record == RecordId['RR']:
            return RecordId['RecordId']


def update_dns(client, value, record, record_id, record_type="A", priority="5", ttl="600"):
    request = UpdateDomainRecordRequest()
    request.set_accept_format('json')

    request.set_Priority(priority)
    request.set_TTL(ttl)
    request.set_Value(value)
    request.set_Type(record_type)
    request.set_RR(record)
    request.set_RecordId(record_id)

    try:
        response = client.do_action_with_exception(request)
    except (ClientException, ServerException) as e:
        logger.error(f"Get update dns error: {e}")
        return None

    return json.loads(str(response, encoding='utf-8'))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Tell me the config file.")
        exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        conf = json.loads(f.read())

        logger = logging.getLogger("ddns")
        logger.setLevel(logging.INFO)
        log_format = ("[%(levelname)s]:%(name)s:%(asctime)s "
                      "(%(filename)s:%(lineno)d %(funcName)s) "
                      "%(process)d %(thread)d "
                      "%(message)s")
        log_formatter = logging.Formatter(log_format)
        time_handle = logging.handlers.TimedRotatingFileHandler(conf["log_file"],
                                                                when="d",
                                                                backupCount=10,
                                                                encoding='utf-8')
        time_handle.setFormatter(log_formatter)
        logger.addHandler(time_handle)

        client = AcsClient(conf["key"], conf["secret"])
        ddns_domain = conf["ddns_domain"]
        ddns_record = conf["ddns_record"]
        ddns_record_id = get_record_id(client, ddns_domain, ddns_record)
        if not ddns_record_id:
            exit(2)

        logger.info(f"Start {ddns_record}.{ddns_domain} id: {ddns_record_id}")

    while True:
        my_ip = get_internet_ip()
        dns_ip = get_dns_ip(client, ddns_record_id)
        if not my_ip or not dns_ip:
            continue
        logger.info(f"Internet ip {my_ip} DNS ip {my_ip}")

        if my_ip != dns_ip:
            result = update_dns(client, my_ip, ddns_record, ddns_record_id)
            if result:
                logger.info(f"DNS update success {my_ip}")
        else:
            time.sleep(10)
