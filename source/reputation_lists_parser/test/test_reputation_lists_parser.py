#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from types import SimpleNamespace

from reputation_lists_parser import reputation_lists
from lib.cw_metrics_util import WAFCloudWatchMetrics
from os import environ
import pytest
import requests

context = SimpleNamespace(**{
    'function_name': 'foo',
    'memory_limit_in_mb': '512',
    'invoked_function_arn': ':::invoked_function_arn',
    'log_group_name': 'log_group_name',
    'log_stream_name': 'log_stream_name',
    'aws_request_id': 'baz'
})

def test_lambda_handler_raises_exception_if_env_variable_not_present(mocker):
    event = {}
    mocker.patch.object(WAFCloudWatchMetrics, 'add_waf_cw_metric_to_usage_data')
    with pytest.raises(TypeError):
        reputation_lists.lambda_handler(event, context)


def test_lambda_handler_returns_error_when_populate_ip_sets_function_fails(mocker):
    event = {}
    environ['URL_LIST'] = '[{"url":"https://www.testmocketenvtest.com"},' \
                          '{"url":"https://www.testmocketenvagaintest.com"}] '
    mocker.patch.object(reputation_lists, 'populate_ipsets', side_effect=Exception('mocked error'))
    mocker.patch.object(requests, 'get')
    response = reputation_lists.lambda_handler(event, context)
    assert response == '{"statusCode": "400", "body": {"message": "mocked error"}}'


def test_lambda_handler_returns_success(mocker):
    event = {}
    environ['URL_LIST'] = '[{"url":"https://www.testmocketenvtest.com"},' \
                          '{"url":"https://www.testmocketenvagaintest.com"}] '
    mocker.patch.object(requests, 'get')
    with open('./test/test_data/test_data.txt', 'r') as file:
        test_data = file.read()
        requests.get.return_value = test_data
        ip_set = {'IPSet':
            {
                'Name': 'prodIPReputationListsSetIPV6',
                'Id': '4342423-d428-4e9d-ba3a-376737347db',
                'ARN': 'arn:aws:wafv2:us-east-1:111111111:regional/ipset/ptestvalue',
                'Description': 'Block Reputation List IPV6 addresses',
                'IPAddressVersion': 'IPV6',
                'Addresses': []
            },
            'LockToken': 'test-token',
            'ResponseMetadata': {
                'RequestId': 'test-id',
                'HTTPStatusCode': 200,
                'HTTPHeaders':
                    {'x-amzn-requestid': 'test-id',
                     'content-type': 'application/x-amz-json-1.1',
                     'content-length': 'test',
                     'date': 'Thu, 27 Apr 2023 03:50:24 GMT'},
                'RetryAttempts': 0
            }
        }
        mocker.patch.object(reputation_lists.waflib, 'update_ip_set')
        mocker.patch.object(reputation_lists.waflib, 'get_ip_set')
        mocker.patch.object(reputation_lists.waflib, 'update_ip_set')
        mocker.patch.object(reputation_lists.waflib, 'get_ip_set')
        mocker.patch.object(WAFCloudWatchMetrics, 'add_waf_cw_metric_to_usage_data')
        reputation_lists.waflib.get_ip_set.return_value = ip_set
        response = reputation_lists.lambda_handler(event, context)
        assert response == '{"StatusCode": "200", "Body": {"message": "success"}}'
